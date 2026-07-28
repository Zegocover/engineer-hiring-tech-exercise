import asyncio
from collections.abc import Awaitable, Callable, Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from crawler.config import DEFAULT_MAX_CONCURRENCY


class UrlNormaliser:
    """Collapses URLs that address the same resource, so one page reached by
    several spellings is only crawled once.

    Used for traversal decisions (the `visited` set and the queue), not for
    the links we report: `found_urls_by_domain` records what a page actually
    linked to, which is a different question from what we chose to fetch.
    """

    # Tracking params tell the target where a visitor came from. They do not
    # select a different resource, so two URLs differing only by these are
    # the same page to a crawler.
    TRACKING_PREFIXES = ("utm_",)
    TRACKING_KEYS = frozenset({"gclid", "fbclid", "mc_cid", "mc_eid"})

    def normalise(self, url: str) -> str:
        """Scheme and host are lowercased (both are case-insensitive per RFC
        3986), a trailing slash is dropped, tracking params are stripped, and
        any fragment is discarded. The path keeps its case, since servers may
        treat it as significant.
        """
        parts = urlsplit(url)

        # "https://example.com/" and "https://example.com" are the same page,
        # but stripping the slash outright would leave an empty path, which
        # urlunsplit renders as a bare host. Keep the root as "/".
        path = parts.path.rstrip("/") or "/"

        query = urlencode(
            [
                (key, value)
                for key, value in parse_qsl(parts.query)
                if not self._is_tracking(key)
            ]
        )

        return urlunsplit(
            (parts.scheme.lower(), parts.netloc.lower(), path, query, "")
        )

    def _is_tracking(self, key: str) -> bool:
        lowered = key.lower()
        return lowered in self.TRACKING_KEYS or lowered.startswith(
            self.TRACKING_PREFIXES
        )


class BredthFirstSearch:
    """Handles the traversal logic for the pages, fetching up to
    max_concurrency pages concurrently via a fixed pool of workers."""

    def __init__(
        self,
        start_url: str,
        get_links: Callable[[str], Awaitable[Iterable[str]]],
        max_concurrency: int = DEFAULT_MAX_CONCURRENCY,
    ) -> None:
        self._normaliser = UrlNormaliser()
        self.start_url = self._normaliser.normalise(start_url)
        self.get_links = get_links
        self.max_concurrency = max_concurrency
        self.visited: set[str] = {self.start_url}
        self.found_urls_by_domain: dict[str, set[str]] = {}
        self._origin_netloc = urlsplit(self.start_url).netloc

    async def run(self) -> tuple[set[str], dict[str, set[str]]]:
        queue: asyncio.Queue[str] = asyncio.Queue()
        queue.put_nowait(self.start_url)

        async def worker() -> None:
            while True:
                url = await queue.get()
                try:
                    links = await self.get_links(url)
                    # No `await` between the membership check and the add
                    # below, so this is safe across concurrent workers
                    # despite `visited` having no lock.
                    for link in links:
                        # Report the link as the page actually wrote it, but
                        # decide what to fetch on the normalised form, so
                        # /page and /page/ are not crawled twice.
                        canonical = self._normaliser.normalise(link)
                        domain = urlsplit(canonical).netloc
                        self.found_urls_by_domain.setdefault(domain, set()).add(link)
                        if domain != self._origin_netloc:
                            continue
                        if canonical not in self.visited:
                            self.visited.add(canonical)
                            queue.put_nowait(canonical)
                finally:
                    queue.task_done()

        workers = [asyncio.create_task(worker()) for _ in range(self.max_concurrency)]
        try:
            await queue.join()
        finally:
            for _worker in workers:
                _worker.cancel()
            await asyncio.gather(*workers, return_exceptions=True)

        return self.visited, self.found_urls_by_domain

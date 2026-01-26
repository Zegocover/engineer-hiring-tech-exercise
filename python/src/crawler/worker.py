"""Worker loop for fetching, parsing, and scheduling."""

from __future__ import annotations

import logging

from crawler import parser, urls
from crawler.config import CrawlerConfig
from crawler.fetcher import (
    Fetcher,
    NonRetryableFetchError,
    RedirectFetchError,
    RetryableFetchError,
    UnsupportedContentTypeError,
)
from crawler.models import CrawlItem
from crawler.renderers import Renderer
from crawler.scheduler import Scheduler

BASE_RETRY_DELAY_S = 1.0
MAX_RETRY_DELAY_S = 10.0


async def worker_loop(
    name: str,
    scheduler: Scheduler,
    fetcher: Fetcher,
    renderer: Renderer,
    cfg: CrawlerConfig,
) -> None:
    """Consume crawl tasks, fetch pages, and enqueue new candidates."""
    while True:
        should_continue = await process_next(
            name=name,
            scheduler=scheduler,
            fetcher=fetcher,
            renderer=renderer,
            cfg=cfg,
        )
        if not should_continue:
            return


async def process_next(
    name: str,
    scheduler: Scheduler,
    fetcher: Fetcher,
    renderer: Renderer,
    cfg: CrawlerConfig | None = None,
) -> bool:
    """Process a single crawl task from the scheduler."""
    if cfg is None:
        raise ValueError("cfg is required")
    item = await scheduler.next_crawl_task()
    if item is None:
        return False
    try:
        logging.debug("%s: fetching %s", name, item.url)
        result = await fetcher.fetch_html(item.url)
        logging.debug(
            "%s: fetched %s (status=%s)",
            name,
            item.url,
            result.status,
        )
        resolved = _extract_and_filter_links(
            body=result.body,
            page_url=item.url,
            strip_fragments=cfg.strip_fragments,
            only_http_links=cfg.only_http_links,
            only_in_scope_links=cfg.only_in_scope_links,
            base_url=cfg.base_url,
        )
        renderer.write_page(_output_page_url(item.url), resolved)
        scheduler.increment_pages_crawled()
        if scheduler.stop_event.is_set():
            return True
        await scheduler.enqueue_candidate_urls(
            resolved,
            depth=item.depth,
        )
    except RedirectFetchError as exc:
        await _handle_redirect(exc, item, scheduler)
    except UnsupportedContentTypeError:
        logging.debug("%s: non-HTML content, skipping %s", name, item.url)
    except NonRetryableFetchError as exc:
        logging.info("%s: non-retryable error for %s: %s", name, item.url, exc)
    except RetryableFetchError as exc:
        if item.attempts + 1 > cfg.profile.max_attempts:
            logging.info(
                "%s: retry limit reached for %s (attempts=%s)",
                name,
                item.url,
                item.attempts + 1,
            )
            return True
        delay = _compute_retry_delay(exc.retry_after, item.attempts)
        logging.debug(
            "%s: retryable error, re-queueing %s after %.1fs (attempt %s)",
            name,
            item.url,
            delay,
            item.attempts + 1,
        )
        await scheduler.enqueue_crawl_task(
            CrawlItem(
                url=item.url,
                depth=item.depth,
                attempts=item.attempts + 1,
            ),
            delay_s=delay,
        )
    finally:
        scheduler.crawl_task_done()
    return True


def _compute_retry_delay(retry_after: str | None, attempts: int) -> float:
    if retry_after is not None:
        try:
            return max(float(retry_after), 0.0)
        except ValueError:
            pass
    delay = BASE_RETRY_DELAY_S * (2**attempts)
    return min(delay, MAX_RETRY_DELAY_S)


def _extract_and_filter_links(
    body: str,
    page_url: str,
    strip_fragments: bool,
    only_http_links: bool,
    only_in_scope_links: bool,
    base_url: str | None,
) -> list[str]:
    links = parser.extract_links(body)
    resolved = [urls.resolve_url(page_url, href) for href in links]
    if strip_fragments:
        resolved = [urls.strip_fragment(link) for link in resolved]
    if only_http_links:
        resolved = _filter_supported_schemes(resolved)
    if only_in_scope_links:
        if base_url is None:
            raise ValueError(
                "base_url is required when only_in_scope_links is enabled"
            )
        resolved = _filter_in_scope_links(resolved, base_url)
    resolved = list(dict.fromkeys(resolved))
    for link in resolved:
        logging.info("🔗 Found link on %s: %s", page_url, link)
    return resolved


async def _handle_redirect(
    exc: RedirectFetchError,
    item: CrawlItem,
    scheduler: Scheduler,
) -> None:
    if exc.location is None:
        return
    redirect_url = urls.resolve_url(item.url, exc.location)
    await scheduler.enqueue_candidate(
        CrawlItem(
            url=redirect_url,
            depth=item.depth,
            attempts=item.attempts,
        )
    )


def _output_page_url(url: str) -> str:
    return urls.normalise_for_dedupe(url)


def _filter_supported_schemes(links: list[str]) -> list[str]:
    filtered: list[str] = []
    for link in links:
        try:
            if urls.is_supported_scheme(link):
                filtered.append(link)
        except urls.UrlParsingError:
            logging.debug("Skipping link with invalid scheme: %s", link)
            continue
    return filtered


def _filter_in_scope_links(links: list[str], base_url: str) -> list[str]:
    filtered: list[str] = []
    for link in links:
        try:
            if urls.is_domain_in_scope(link, base_url):
                filtered.append(link)
        except urls.UrlParsingError:
            logging.debug("Skipping link with invalid domain: %s", link)
            continue
    return filtered

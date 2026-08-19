from urllib.parse import urlsplit, urlunsplit


class UrlPolicy:
    """Defines which normalized URLs belong to the crawl's exact host."""

    def __init__(self, base_url: str) -> None:
        parsed = urlsplit(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError(
                "base URL must include an HTTP(S) scheme and hostname"
            )
        self._host = parsed.hostname.lower()

    def normalize(self, url: str) -> str | None:
        """Return a fragment-free HTTP(S) URL on the base host, if eligible."""
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"} or parsed.hostname is None:
            return None
        if parsed.hostname.lower() != self._host:
            return None

        return urlunsplit(
            (
                parsed.scheme.lower(),
                parsed.netloc,
                parsed.path or "/",
                parsed.query,
                "",
            )
        )

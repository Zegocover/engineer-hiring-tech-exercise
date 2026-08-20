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

        userinfo, separator, host_port = parsed.netloc.rpartition("@")
        if host_port.startswith("["):
            closing_bracket = host_port.index("]")
            canonical_host_port = (
                f"[{host_port[1:closing_bracket].lower()}]"
                f"{host_port[closing_bracket + 1:]}"
            )
        else:
            host, port_separator, port = host_port.partition(":")
            canonical_host_port = (
                f"{host.lower()}{port_separator}{port}"
            )
        canonical_netloc = (
            f"{userinfo}{separator}{canonical_host_port}"
        )

        return urlunsplit(
            (
                parsed.scheme.lower(),
                canonical_netloc,
                parsed.path or "/",
                parsed.query,
                "",
            )
        )

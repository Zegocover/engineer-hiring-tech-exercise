"""Host patterns that widen a crawl's scope beyond its base host."""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from urllib.parse import urlsplit

from site_crawler.models.errors import ConfigError

_LABEL = re.compile(r"^(?!-)[a-z0-9-]{1,63}(?<!-)$")
_FORBIDDEN = re.compile(r"[\s/@?#\\]|://")


@dataclass(frozen=True, slots=True)
class HostPattern:
    """An exact host (optionally with a port) or a ``*.domain`` subdomain wildcard.

    ``host`` is lowercase without a trailing dot; IPv6 literals are kept without
    brackets. ``port`` is ``None`` for default ports. Wildcards never carry a port.
    """

    host: str
    port: int | None = None
    wildcard: bool = False

    def matches(self, hostname: str, port: int | None) -> bool:
        """Whether a URL with this hostname and non-default ``port`` is covered."""
        if self.wildcard:
            return port is None and hostname.endswith("." + self.host)
        return hostname == self.host and port == self.port

    def __str__(self) -> str:
        if self.wildcard:
            return f"*.{self.host}"
        host = f"[{self.host}]" if ":" in self.host else self.host
        return host if self.port is None else f"{host}:{self.port}"


def parse_host_pattern(text: str) -> HostPattern:
    """Parse ``docs.partner.io``, ``localhost:8001``, ``[::1]:8080`` or ``*.example.com``.

    Raises :class:`ConfigError` naming the pattern if it is anything else (a URL,
    a path, a bare ``*`` or a ``*`` other than a leading ``*.``).
    """
    original = text
    text = text.strip().lower()

    def invalid(reason: str) -> ConfigError:
        return ConfigError(f"invalid host pattern {original!r}: {reason}")

    if not text:
        raise invalid("it is empty")
    if _FORBIDDEN.search(text):
        raise invalid("use a host name only, without scheme, path or credentials")

    wildcard = text.startswith("*.")
    if wildcard:
        text = text[2:]
    if "*" in text:
        raise invalid("'*' is only allowed as a leading '*.'")

    try:
        parts = urlsplit(f"//{text}")
        hostname, port = parts.hostname, parts.port
    except ValueError as exc:
        raise invalid(str(exc)) from None
    if not hostname:
        raise invalid("it has no host name")
    hostname = hostname.rstrip(".")
    if wildcard and port is not None:
        raise invalid("a '*.' wildcard cannot have a port")
    if port in (80, 443):
        port = None  # default ports are ignored, as in URL matching

    if not _is_ip(hostname):
        labels = hostname.split(".")
        if not all(_LABEL.match(label) for label in labels):
            raise invalid("not a valid host name")
    elif wildcard:
        raise invalid("a '*.' wildcard needs a domain name, not an IP address")

    return HostPattern(host=hostname, port=port, wildcard=wildcard)


def _is_ip(hostname: str) -> bool:
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        return False
    return True

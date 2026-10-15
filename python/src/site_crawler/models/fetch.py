from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class FetchResult:
    """A fetched resource.

    ``final_url`` is the URL after redirects; relative links on the page are
    resolved against it.
    """

    url: str
    final_url: str
    status: int
    content_type: str | None
    body: bytes = field(repr=False)

    @property
    def is_html(self) -> bool:
        if self.content_type is None:
            return False
        mime = self.content_type.split(";", 1)[0].strip().lower()
        return mime in ("text/html", "application/xhtml+xml")

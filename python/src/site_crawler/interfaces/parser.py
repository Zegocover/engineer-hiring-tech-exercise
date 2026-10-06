from __future__ import annotations

from typing import Protocol

from site_crawler.models import FetchResult


class Parser(Protocol):
    def parse(self, page: FetchResult) -> list[str]:
        """Return link strings found in ``page``.

        Strings may be relative; the crawler resolves them against
        ``page.final_url``. A parser that honours ``<base href>`` should
        return links already joined with it.
        """
        ...

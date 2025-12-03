from __future__ import annotations

import logging
from typing import Optional, Tuple

from aiohttp import ClientSession


class Fetcher:
    async def fetch(self, session: ClientSession, url: str) -> Optional[Tuple[str, str]]:
        try:
            async with session.get(url, allow_redirects=True) as resp:
                ctype = resp.headers.get("Content-Type", "")
                if resp.status != 200 or "html" not in ctype:
                    return None
                text = await resp.text(errors="ignore")
                return (str(resp.url), text)
        except Exception:
            logging.exception(f"Error fetching {url}")
            return None
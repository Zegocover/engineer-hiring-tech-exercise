from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from urllib.parse import urldefrag, urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup


@dataclass(frozen=True)
class PageResult:
    url: str
    links: list[str] = field(default_factory=list)
    crawlable_links: list[str] = field(default_factory=list)
    status: int | None = None
    error: str | None = None

    def to_text(self) -> str:
        lines = [self.url]
        for link in self.links:
            lines.append(f"  {link}")
        if self.error:
            lines.append(f"  [error] {self.error}")
        return "\n".join(lines)


@dataclass(frozen=True)
class WorkItem:
    url: str
    attempts: int = 0


class PageWorker:
    def __init__(
        self,
        *,
        base_url: str,
        timeout: float = 10.0,
        retries: int = 1,
        user_agent: str = "ZegoCrawler/1.0",
    ) -> None:
        parsed = urlparse(base_url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("base_url must include scheme and domain")
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("base_url must start with http:// or https://")
        self.base_url = base_url
        self.base_netloc = parsed.netloc
        self.timeout = timeout
        self.retries = retries
        self.user_agent = user_agent

    async def fetch(self, url: str) -> PageResult:
        last_error: str | None = None
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        headers = {"User-Agent": self.user_agent}

        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            for attempt in range(self.retries + 1):
                try:
                    async with session.get(url, allow_redirects=True) as response:
                        final_url = str(response.url)
                        if urlparse(final_url).netloc != self.base_netloc:
                            return PageResult(
                                url=url,
                                links=[],
                                crawlable_links=[],
                                status=response.status,
                                error="redirected to external domain",
                            )
                        content_type = response.headers.get("content-type", "")
                        text = await response.text(errors="ignore")
                        links: list[str] = []
                        crawlable_links: list[str] = []
                        if _looks_like_html(content_type, text):
                            links = extract_links(
                                html=text,
                                base_url=url,
                            )
                            crawlable_links = filter_same_domain_links(
                                links=links,
                                base_netloc=self.base_netloc,
                            )
                        return PageResult(
                            url=url,
                            links=links,
                            crawlable_links=crawlable_links,
                            status=response.status,
                        )
                except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                    last_error = str(exc)
                    if attempt >= self.retries:
                        break
                except Exception as exc:  # pragma: no cover - defensive fallback
                    last_error = str(exc)
                    break

        return PageResult(url=url, links=[], crawlable_links=[], error=last_error)


def normalize_url(base_url: str, href: str) -> str | None:
    if not href:
        return None
    absolute = urljoin(base_url, href)
    absolute, _ = urldefrag(absolute)
    parsed = urlparse(absolute)
    if parsed.scheme not in {"http", "https"}:
        return None
    if not parsed.netloc:
        return None
    return parsed._replace(fragment="").geturl()


def extract_links(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []
    seen: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        normalized = normalize_url(base_url, anchor.get("href"))
        if not normalized:
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        links.append(normalized)
    return links


def filter_same_domain_links(*, links: list[str], base_netloc: str) -> list[str]:
    return [link for link in links if urlparse(link).netloc == base_netloc]


def _looks_like_html(content_type: str, text: str) -> bool:
    return "text/html" in content_type.lower() or "<html" in text[:1000].lower()

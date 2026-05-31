import httpx
import typer
from asyncer import runnify

from crawler.builder import build_crawler
from crawler.output import format_jsonl, format_text
from domains.crawler.models import CrawlConfig
from domains.crawler.urls import extract_host

app = typer.Typer(
    no_args_is_help=True,
    help="Single-domain web crawler.",
)


@app.callback()
def main() -> None:
    pass


@app.command()
@runnify
async def crawl(
    url: str = typer.Argument(..., help="Base URL to crawl."),
    concurrency: int = typer.Option(10, help="Number of concurrent fetch workers."),
    timeout: float = typer.Option(10.0, help="Per-request timeout in seconds."),
    max_pages: int | None = typer.Option(None, help="Stop after this many pages."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSONL instead of text."),
) -> None:
    """Crawl URL within its own domain and print discovered links."""
    host = extract_host(url)
    if not host:
        typer.echo(f"error: '{url}' has no host to crawl", err=True)
        raise typer.Exit(code=2)

    config = CrawlConfig(
        seed_url=url,
        seed_host=host,
        concurrency=concurrency,
        timeout=timeout,
        max_pages=max_pages,
    )
    render = format_jsonl if json_output else format_text

    timeout_cfg = httpx.Timeout(timeout)
    headers = {"user-agent": config.user_agent}
    async with httpx.AsyncClient(timeout=timeout_cfg, headers=headers) as client:
        crawler = build_crawler(config, client)
        async for page in crawler.crawl():
            typer.echo(render(page))

    if getattr(crawler, "truncated", False):
        typer.echo(f"notice: stopped at max-pages={max_pages}", err=True)

"""CLI interface for the web crawler."""

import asyncio

import typer

from crawler.crawler import Crawler

app = typer.Typer(help="Async web crawler that crawls a single domain.")


def print_page(url: str, found_urls: list[str]) -> None:
    """Print crawl results for a page."""
    typer.echo(f"\nCrawling: {url}")
    if found_urls:
        typer.echo("  Found URLs:")
        for found_url in found_urls:
            typer.echo(f"    - {found_url}")
    else:
        typer.echo("  No URLs found")


@app.command()
def crawl(
    url: str = typer.Argument(..., help="The URL to start crawling from"),
    max_concurrency: int = typer.Option(10, help="Maximum concurrent requests"),
    timeout: float = typer.Option(30.0, help="Request timeout in seconds"),
) -> None:
    """Crawl a website starting from the given URL."""
    typer.echo(f"Starting crawl from: {url}")
    typer.echo(f"Max concurrency: {max_concurrency}, Timeout: {timeout}s")

    crawler = Crawler(
        start_url=url,
        max_concurrency=max_concurrency,
        timeout=timeout,
        on_page_crawled=print_page,
    )

    results = asyncio.run(crawler.crawl())

    typer.echo(f"\n\nCrawl complete. Total pages crawled: {len(results)}")


if __name__ == "__main__":
    app()

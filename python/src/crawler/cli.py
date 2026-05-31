import typer
from asyncer import runnify

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
) -> None:
    """Crawl URL within its own domain and print discovered links."""
    typer.echo(f"crawl: not implemented (url={url})")
    raise typer.Exit(code=1)

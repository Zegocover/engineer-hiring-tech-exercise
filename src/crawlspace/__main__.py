import argparse
import asyncio

from .schemas import PageReport, SiteReport


async def main(base_url: str) -> SiteReport:
    return SiteReport(
        pages=[
            PageReport(
                url="http://localhost:8888",
                status=200,
                links=["http://localhost:8888/empty-page"],
            ),
            PageReport(
                url="http://localhost:8888/empty-page",
                status=200,
                links=[],
            ),
        ]
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process a URL.")
    parser.add_argument("url", type=str, help="The URL to process.")
    args = parser.parse_args()

    report = asyncio.run(main(args.url))

    for page in report.pages:
        print(f"{page.status} {page.url}")
        if not page.links:
            print(" * No links *")
            continue

        for link in page.links:
            print(f" - {link}")

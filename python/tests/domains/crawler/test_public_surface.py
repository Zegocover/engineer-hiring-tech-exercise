def test_public_names_importable_from_package_root() -> None:
    from domains.crawler import (
        CrawlConfig,
        Crawler,
        FetchResult,
        LinkParser,
        PageResult,
        ParseOutcome,
    )

    assert Crawler is not None
    assert CrawlConfig is not None
    assert LinkParser is not None
    assert FetchResult is not None
    assert PageResult is not None
    assert ParseOutcome is not None

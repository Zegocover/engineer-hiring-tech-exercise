import pytest
from web_crawler import WebCrawler


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_target(run_live_tests, live_test_target):
    if not run_live_tests:
        pytest.skip("Live tests not enabled (use --live-target)")
    target = live_test_target
    if not target:
        pytest.skip("Pass target URL to --live-target to enable live tests")
    c = WebCrawler(target, concurrency=2, max_pages=5)
    await c.crawl()
    assert len(c.visited) >= 1

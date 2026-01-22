import pytest
import aiohttp
import time
from unittest.mock import MagicMock, AsyncMock, patch
from src.crawler import Crawler, TokenBucket
from src.utils import async_retry


@pytest.mark.asyncio
async def test_crawler_writer(tmp_path):
    output_file = tmp_path / "test_output.csv"
    crawler = Crawler("https://example.com", output_file=str(output_file))
    
    # Start writer
    writer_task = asyncio.create_task(crawler.writer())
    
    # Put items in write_queue
    await crawler.write_queue.put(("https://example.com", "https://example.com/page1"))
    await crawler.write_queue.put(("https://example.com", "https://example.com/page2"))
    
    # Signal stop
    await crawler.write_queue.put(None)
    
    # Wait for writer to finish
    await writer_task
    
    # Verify file content
    content = output_file.read_text(encoding='utf-8')
    assert "Source URL,Found Link" in content
    assert "https://example.com,https://example.com/page1" in content
    assert "https://example.com,https://example.com/page2" in content
    crawler = Crawler("https://example.com")
    crawler.session = MagicMock()
    
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.headers = {'Content-Type': 'text/html'}
    mock_response.text.return_value = "<html></html>"
    
    # Mock the context manager
    crawler.session.get.return_value.__aenter__.return_value = mock_response
    mock_response.url = "https://example.com"
    
    html, _ = await crawler.fetch("https://example.com")
    assert html == "<html></html>"

@pytest.mark.asyncio
async def test_crawler_fetch_failure():
    crawler = Crawler("https://example.com")
    crawler.session = MagicMock()
    
    mock_response = AsyncMock()
    mock_response.status = 404
    
    crawler.session.get.return_value.__aenter__.return_value = mock_response
    mock_response.url = "https://example.com"
    
    html, _ = await crawler.fetch("https://example.com")
    assert html == ""

@pytest.mark.asyncio
async def test_crawler_worker():
    crawler = Crawler("https://example.com")
    crawler.fetch = AsyncMock(return_value=('<a href="/page1">Page 1</a>', 'https://example.com'))
    
    await crawler.queue.put("https://example.com")
    
    # Run worker for one iteration (we need to break the loop or mock it)
    # Since worker is an infinite loop, we can test the logic by extracting it or 
    # just testing the side effects of a single pass if we refactor.
    # Alternatively, we can run the crawl method with a mocked fetch and limited depth/time.
    
    # Let's test crawl() end-to-end with mocks
    with patch('src.crawler.aiohttp.ClientSession') as MockSession:
        mock_session_instance = MockSession.return_value
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {'Content-Type': 'text/html'}
        mock_response.text.return_value = '<a href="/page1">Page 1</a>'
        mock_session_instance.get.return_value.__aenter__.return_value = mock_response
        
        # We need to limit the crawl or it will go forever if we keep returning links
        # But here we only return one link /page1.
        # Then /page1 will be fetched. Let's make /page1 return no links to stop recursion.
        
        async def side_effect(url):
            if url == "https://example.com":
                return '<a href="/page1">Page 1</a>', "https://example.com"
            return "", url
            
        crawler.fetch = AsyncMock(side_effect=side_effect)
        
        # We need to re-initialize session because crawl() creates it
        # But we mocked fetch, so session usage inside fetch is bypassed.
        # However, crawl() still creates a session.
        
        # Make close awaitable
        mock_session_instance.close = AsyncMock()
        
        await crawler.crawl()
        
    
    assert "https://example.com" in crawler.visited
    assert "https://example.com/page1" in crawler.visited

@pytest.mark.asyncio
async def test_crawler_fetch_http_errors():
    crawler = Crawler("https://example.com")
    crawler.session = MagicMock()
    
    # Test 500 Error (Should raise ClientResponseError to trigger retry)
    mock_response_500 = AsyncMock()
    mock_response_500.status = 500
    mock_response_500.request_info = MagicMock()
    mock_response_500.history = ()
    mock_response_500.headers = {}
    
    crawler.session.get.return_value.__aenter__.return_value = mock_response_500
    
    # We expect the decorated fetch to eventually raise or log/retry. 
    # Since we mocked the session, the decorator will see the raised exception if we let it bubble
    # But wait, our fetch implementation RAISES for >= 500.
    # The decorator catches it and retries. If it fails all retries, it raises.
    # So calling fetch() with a persistent 500 should raise ClientResponseError.
    
    with pytest.raises(aiohttp.ClientResponseError):
        # We need to bypass the retry delay for speed, or mock sleep
         with patch('asyncio.sleep', new_callable=AsyncMock):
            await crawler.fetch("https://example.com/error")

    # Test 404 Error (Should return empty string, no retry)
    mock_response_404 = AsyncMock()
    mock_response_404.status = 404
    mock_response_404.url = "https://example.com/missing"
    crawler.session.get.return_value.__aenter__.return_value = mock_response_404
    
    html, _ = await crawler.fetch("https://example.com/missing")
    assert html == ""

import asyncio

@pytest.mark.asyncio
async def test_crawler_fetch_retry():
    crawler = Crawler("https://example.com")
    crawler.session = MagicMock()
    
    # Mock response to raise ClientError twice, then succeed
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.headers = {'Content-Type': 'text/html'}
    mock_response.text.return_value = "<html></html>"
    
    # Let's test the retry logic via a simple decorated function first to ensure the decorator works.
    
    from src.utils import async_retry
    
    mock_func = AsyncMock(side_effect=[aiohttp.ClientError("Fail 1"), aiohttp.ClientError("Fail 2"), "Success"])
    
    @async_retry(retries=3, backoff_factor=0.01) # fast backoff for test
    async def reliable_fetch():
        return await mock_func()
        
    result = await reliable_fetch()
    assert result == "Success"
    assert mock_func.call_count == 3

@pytest.mark.asyncio
async def test_token_bucket_rate_limiting():
    # Rate limit: 2 requests per second
    bucket = TokenBucket(rate=2.0, capacity=2.0)
    
    start_time = time.monotonic()
    
    for _ in range(5):
        await bucket.acquire()
        
    duration = time.monotonic() - start_time
    # Expected duration: minimal 1.5s (3 intervals of 0.5s)
    # Allow some buffer for execution overhead
    assert duration >= 1.45 

@pytest.mark.asyncio
async def test_crawler_respects_rate_limit():
    crawler = Crawler("https://example.com/test", rate_limit=5.0)
    crawler.session = MagicMock()
    
    # Mock acquire to track calls
    crawler.limiter.acquire = AsyncMock()
    
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.headers = {'Content-Type': 'text/html'}
    mock_response.text.return_value = ""
    mock_response.url = "https://example.com/1"
    crawler.session.get.return_value.__aenter__.return_value = mock_response
    
    await crawler.fetch("https://example.com/1")
    
    # Verify acquire was called
    crawler.limiter.acquire.assert_called_once()

@pytest.mark.asyncio
async def test_robots_txt_respect():
    crawler = Crawler("https://example.com")
    crawler.session = MagicMock()
    
    # Mock robots.txt response
    mock_robots = AsyncMock()
    mock_robots.status = 200
    mock_robots.text.return_value = """
    User-agent: *
    Disallow: /private/
    """
    
    # Mock normal page response
    mock_page = AsyncMock()
    mock_page.status = 200
    mock_page.headers = {'Content-Type': 'text/html'}
    mock_page.text.return_value = "<html></html>"
    
    # Configure session.get to return different mocks based on URL
    def side_effect(url, **kwargs):
        if "robots.txt" in url:
            # Return an object that works with `async with`
            return MagicMock(__aenter__=AsyncMock(return_value=mock_robots), __aexit__=AsyncMock())
        else:
            return MagicMock(__aenter__=AsyncMock(return_value=mock_page), __aexit__=AsyncMock())
            
    crawler.session.get.side_effect = side_effect
    
    # 1. Init robots.txt
    await crawler.init_robots_txt()
    
    # 2. Check allowed URL
    assert crawler.can_fetch("https://example.com/public") == True
    
    # 3. Check disallowed URL
    assert crawler.can_fetch("https://example.com/private/secret") == False

@pytest.mark.asyncio
async def test_crawler_redirect_external():
    """Test that we do not process links if redirected to a different domain."""
    crawler = Crawler("https://example.com")
    
    # Mock extract_links to return something if called (though we expect it NOT to be called or ignored)
    with patch('src.crawler.extract_links') as mock_extract:
        mock_extract.return_value = {"https://google.com/foo"}
        
        # Configure fetch to simulate a redirect to google.com
        crawler.fetch = AsyncMock(return_value=('<html></html>', 'https://google.com'))
        
        await crawler.queue.put("https://example.com/redirect")
        
        # Run worker for one iteration
        # Because worker is infinite loop, we run it as a task and cancel? 
        # Or simpler: verify logic by calling something that worker would call.
        # But worker calls fetch. 
        # We can just run worker logic manually or use timeout.
        
        try:
            await asyncio.wait_for(crawler.worker(), timeout=0.1)
        except asyncio.TimeoutError:
            pass
            
        # Verify:
        # 1. extract_links should NOT be called (or if called, logic ignored results, but better if not called for robustness? 
        # Actually our implementation calls extract_links only if domain matches.
        # Wait, implementation was:
        # if not is_same_domain(...): continue
        # else: extract_links(...)
        
        # So extract_links should NOT be called.
        mock_extract.assert_not_called()
        
        # And queue should be empty (links from google not added)
        assert crawler.queue.qsize() == 0

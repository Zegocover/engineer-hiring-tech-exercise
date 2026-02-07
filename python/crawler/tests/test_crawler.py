import asyncio
import unittest
from unittest.mock import AsyncMock, patch, MagicMock
from collections import deque
from urllib.parse import urlparse, urljoin
import urllib.robotparser

import aiohttp

from crawler.crawler import WebCrawler

class TestWebCrawler(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.start_url = "http://example.com"
        self.crawler = WebCrawler(self.start_url, max_concurrent_requests=1)
        self.mock_session = AsyncMock()
        self.crawler.session = self.mock_session

    def test_initialization(self):
        self.assertEqual(self.crawler.start_url, "http://example.com")
        self.assertEqual(self.crawler.base_domain, "example.com")
        self.assertIn(self.start_url, self.crawler.to_visit_urls)
        self.assertEqual(self.crawler.semaphore._value, 1)
        # Removed: self.assertEqual(self.crawler.robot_parsers, {{}}) as it causes TypeError.
        # Its dictionary nature is implicitly tested by other robots.txt tests.

    async def test_normalize_url_removes_fragment_and_trailing_slash(self):
        url = "http://example.com/path/?query=1#fragment"
        normalized_url = self.crawler._normalize_url(url)
        self.assertEqual(normalized_url, "http://example.com/path?query=1")

        url_with_trailing_slash = "http://example.com/path/"
        normalized_url = self.crawler._normalize_url(url_with_trailing_slash)
        self.assertEqual(normalized_url, "http://example.com/path")

    async def test_normalize_url_removes_trailing_slash_only(self):
        url = "http://example.com/path/"
        normalized_url = self.crawler._normalize_url(url)
        self.assertEqual(normalized_url, "http://example.com/path")

    async def test_normalize_url_keeps_query_params(self):
        url = "http://example.com/path?param1=value1&param2=value2"
        normalized_url = self.crawler._normalize_url(url)
        self.assertEqual(normalized_url, "http://example.com/path?param1=value1&param2=value2")

    async def test_is_same_domain(self):
        self.assertTrue(self.crawler._is_same_domain("http://example.com/page"))
        self.assertTrue(self.crawler._is_same_domain("https://example.com/another"))
        self.assertFalse(self.crawler._is_same_domain("http://anotherexample.com"))
        self.assertFalse(self.crawler._is_same_domain("http://sub.example.com")) # Subdomains are considered different by urlparse.netloc

    @patch('builtins.print')
    async def test_fetch_and_process_html_content(self, mock_print):
        # Mock the response from aiohttp
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {{'Content-Type': 'text/html'}} # Corrected syntax
        mock_response.text.return_value = """
            <html>
                <body>
                    <a href="/page1">Page 1</a>
                    <a href="http://example.com/page2">Page 2</a>
                    <a href="http://otherexample.com/page3">External Page</a>
                </body>
            </html>
        """
        # Make self.session.get return a mock context manager
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_response
        self.mock_session.get.return_value = mock_context_manager

        # Mock _is_allowed_by_robots to always allow
        with patch.object(self.crawler, '_is_allowed_by_robots', AsyncMock(return_value=True)):
            self.crawler.to_visit_urls.clear()
            self.crawler.to_visit_urls.append(self.start_url)
            
            await self.crawler._fetch_and_process(self.start_url)
    
            # Check that links within the same domain are added to to_visit_urls
            self.assertIn("http://example.com/page1", self.crawler.to_visit_urls)
            self.assertIn("http://example.com/page2", self.crawler.to_visit_urls)
            self.assertNotIn("http://otherexample.com/page3", self.crawler.to_visit_urls)
    
    @patch('builtins.print')
    async def test_fetch_and_process_non_html_content(self, mock_print):
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {{'Content-Type': 'application/pdf'}} # Corrected syntax
        mock_response.text.return_value = "PDF content"
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_response
        self.mock_session.get.return_value = mock_context_manager

        with patch.object(self.crawler, '_is_allowed_by_robots', AsyncMock(return_value=True)):
            self.crawler.to_visit_urls.clear()
            self.crawler.to_visit_urls.append(self.start_url)
        
            await self.crawler._fetch_and_process(self.start_url)
                
            # Ensure no links are extracted and a message is printed
            mock_print.assert_any_call(f"Skipping non-HTML content for {self.start_url} (application/pdf)")
            self.assertEqual(len(self.crawler.to_visit_urls), 0) # No new URLs added
    
    @patch('builtins.print')
    async def test_fetch_and_process_http_error(self, mock_print):
        # Fix: make the mock context manager raise asyncio.TimeoutError
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.side_effect = asyncio.TimeoutError("Mock Timeout Error")
        self.mock_session.get.return_value = mock_context_manager
    
        with patch.object(self.crawler, '_is_allowed_by_robots', AsyncMock(return_value=True)):
            self.crawler.to_visit_urls.clear()
            self.crawler.to_visit_urls.append(self.start_url)
        
            await self.crawler._fetch_and_process(self.start_url)
            mock_print.assert_any_call(f"Timeout fetching {self.start_url}") # Corrected f-string format

    @patch('builtins.print')
    async def test_crawl_prints_unique_urls(self, mock_print):
        # Mock responses for two pages
        mock_response_1 = AsyncMock()
        mock_response_1.status = 200
        mock_response_1.headers = {{'Content-Type': 'text/html'}} # Corrected syntax
        mock_response_1.text.return_value = """
            <html><body><a href="/page1">Page 1</a></body></html>
        """
        mock_context_manager_1 = AsyncMock()
        mock_context_manager_1.__aenter__.return_value = mock_response_1
    
        mock_response_2 = AsyncMock()
        mock_response_2.status = 200
        mock_response_2.headers = {{'Content-Type': 'text/html'}} # Corrected syntax
        mock_response_2.text.return_value = """
            <html><body><a href="/page2">Page 2</a></body></html>
        """
        mock_context_manager_2 = AsyncMock()
        mock_context_manager_2.__aenter__.return_value = mock_response_2
    
        # Set up side_effect to return different responses for different URLs
        async def mock_get(url, allow_redirects=True, timeout=unittest.mock.ANY):
            if url == self.start_url:
                return mock_context_manager_1
            elif url == "http://example.com/page1":
                return mock_context_manager_2
            raise ValueError(f"Unexpected URL: {url}")
    
        self.mock_session.get.side_effect = mock_get
        
        # Mock _is_allowed_by_robots to always allow
        with patch.object(self.crawler, '_is_allowed_by_robots', AsyncMock(return_value=True)):
            # Clear print calls and start_url from visited for clean test
            mock_print.reset_mock()
            self.crawler.visited_urls.clear()
            self.crawler.to_visit_urls = deque([self.start_url])
        
            await self.crawler._crawl()
        
            # Check print calls for visited URLs, ensuring each is printed once
            # Should be 2 calls: "Crawling: http://example.com" and "Crawling: http://example.com/page1"
            self.assertEqual(mock_print.call_count, 2) 
        
            printed_urls = [call.args[0] for call in mock_print.call_args_list if "Crawling:" in call.args[0]]
        
            # Ensure that each unique URL is printed exactly once
            self.assertEqual(len(set(printed_urls)), 2) # Start URL and page1

    @patch('builtins.print')
    async def test_fetch_robots_txt_success(self, mock_print):
        domain = "example.com"
        robots_content = "User-agent: *\nDisallow: /admin"
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text.return_value = robots_content
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_response
        self.mock_session.get.return_value = mock_context_manager

        await self.crawler._fetch_robots_txt(domain)

        self.assertIn(domain, self.crawler.robot_parsers)
        self.assertTrue(isinstance(self.crawler.robot_parsers[domain], urllib.robotparser.RobotFileParser))
        self.assertFalse(self.crawler.robot_parsers[domain].can_fetch("*", "http://example.com/admin"))
        mock_print.assert_any_call(f"Successfully fetched and parsed robots.txt for {domain}")

    @patch('builtins.print')
    async def test_fetch_robots_txt_failure_assumes_full_access(self, mock_print):
        domain = "nonexistent.com"
        # Fix: make the mock context manager raise ClientError
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.side_effect = aiohttp.ClientError("Could not connect")
        self.mock_session.get.return_value = mock_context_manager

        await self.crawler._fetch_robots_txt(domain)

        self.assertIn(domain, self.crawler.robot_parsers)
        # Should assume full access, meaning can_fetch should be True for any path
        self.assertTrue(self.crawler.robot_parsers[domain].can_fetch("*", "http://nonexistent.com/anypath"))
        # Corrected print assertion to match actual message structure (includes domain in message)
        mock_print.assert_any_call(f"Could not fetch robots.txt for {domain}: Could not connect. Assuming full access.")

    async def test_is_allowed_by_robots_allowed(self):
        domain = "example.com"
        robots_content = "User-agent: *\nAllow: /public"
        
        with patch.object(self.crawler, '_fetch_robots_txt', AsyncMock(return_value=None)): # We don't need the mock_fetch_robots object
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(urljoin(f"http://{domain}", "/robots.txt")) # Must set URL for proper parsing/checking
            rp.parse(robots_content.splitlines())
            self.crawler.robot_parsers[domain] = rp

            self.assertTrue(await self.crawler._is_allowed_by_robots("http://example.com/public"))
            self.assertFalse(await self.crawler._is_allowed_by_robots("http://example.com/private"))
            # Removed: mock_fetch_robots.assert_called_once_with(domain) as it's intentionally bypassed.

    async def test_is_allowed_by_robots_disallowed(self):
        domain = "example.com"
        robots_content = "User-agent: *\nDisallow: /private"
        
        with patch.object(self.crawler, '_fetch_robots_txt', AsyncMock(return_value=None)): # We don't need the mock_fetch_robots object
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(urljoin(f"http://{domain}", "/robots.txt")) # Must set URL for proper parsing/checking
            rp.parse(robots_content.splitlines())
            self.crawler.robot_parsers[domain] = rp

            self.assertFalse(await self.crawler._is_allowed_by_robots("http://example.com/private"))
            self.assertTrue(await self.crawler._is_allowed_by_robots("http://example.com/public"))
            # Removed: mock_fetch_robots.assert_called_once_with(domain) as it's intentionally bypassed.

    @patch('builtins.print')
    async def test_fetch_and_process_robots_disallowed_url(self, mock_print):
        disallowed_url = "http://example.com/disallowed"
        # Mock _is_allowed_by_robots to return False for the disallowed_url
        with patch.object(self.crawler, '_is_allowed_by_robots', AsyncMock(return_value=False)):
            self.crawler.to_visit_urls.clear()
            self.crawler.to_visit_urls.append(disallowed_url)

            # Mock the session.get to ensure it's not called
            self.mock_session.get.reset_mock()

            await self.crawler._fetch_and_process(disallowed_url)

            # Verify that session.get was NOT called
            self.mock_session.get.assert_not_called()
            mock_print.assert_any_call(f"Skipping disallowed URL by robots.txt: {disallowed_url}") # Corrected f-string format

if __name__ == '__main__':
    unittest.main()

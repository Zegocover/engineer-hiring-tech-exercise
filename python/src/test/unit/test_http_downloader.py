import hashlib
import os
import unittest
from unittest.mock import patch, MagicMock
from urlcrawler.http_downloader import HttpDownloader


class TestHttpDownloader(unittest.TestCase):
    def tearDown(self):
        # Clean up cache directory after each test
        cache_dir = "./cache"
        if os.path.exists(cache_dir):
            for file in os.listdir(cache_dir):
                os.remove(os.path.join(cache_dir, file))
            os.rmdir(cache_dir)

    @patch("urlcrawler.http_downloader.requests.get")
    def test_get_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "hello world"
        mock_get.return_value = mock_response

        downloader = HttpDownloader(use_cache=False)
        result = downloader.get("http://example.com")
        self.assertEqual(result, "hello world")
        mock_get.assert_called_once_with("http://example.com")

    @patch("urlcrawler.http_downloader.requests.get")
    def test_get_http_error(self, mock_get):
        mock_get.side_effect = Exception("Network error")
        downloader = HttpDownloader(use_cache=False)
        with self.assertRaises(Exception):
            downloader.get("http://example.com")

    def test_cache(self):
        downloader = HttpDownloader(use_cache=True)
        url = "http://example.com"
        filename = f"./cache/{hashlib.md5(url.encode("utf-8")).hexdigest()}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write("cached content")
        result = downloader.get(url)
        self.assertEqual(result, "cached content")

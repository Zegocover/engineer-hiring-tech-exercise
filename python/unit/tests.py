import unittest
from unittest.mock import patch

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import validate_url_domain

class FakeConfig:
    def __init__(self, domain):
        self.domain = domain

class TestValidateUrlDomain(unittest.TestCase):

    @patch("main.Config")
    def test_domain_matches(self, MockConfig):
        # Domain of url matches the one in config
        MockConfig.return_value = FakeConfig(domain="example.com")
        url = "https://example.com/page"
        result = validate_url_domain(url)
        self.assertTrue(result)

    @patch("main.Config")
    def test_domain_does_not_match(self, MockConfig):
        # Domain of url does not match the config domain
        MockConfig.return_value = FakeConfig(domain="example.com")
        url = "https://notexample.com/page"
        result = validate_url_domain(url)
        self.assertFalse(result)
    
    @patch("main.Config")
    def test_domain_matches_with_port(self, MockConfig):
        MockConfig.return_value = FakeConfig(domain="example.com")
        url = "https://example.com:8080/page"
        result = validate_url_domain(url)
        self.assertTrue(result)

    @patch("main.Config")
    def test_domain_is_subdomain(self, MockConfig):
        MockConfig.return_value = FakeConfig(domain="example.com")
        url = "https://sub.example.com/page"
        result = validate_url_domain(url)
        self.assertFalse(result)

    @patch("main.Config")
    def test_config_domain_with_port(self, MockConfig):
        # config.domain does not include port, but url has it
        MockConfig.return_value = FakeConfig(domain="example.com")
        url = "http://example.com:443"
        result = validate_url_domain(url)
        self.assertTrue(result)

if __name__ == "__main__":
    unittest.main()

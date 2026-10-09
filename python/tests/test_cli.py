"""Tests for the CLI module."""

import pytest

from crawler.cli import validate_url


class TestValidateUrl:
    """Tests for URL validation and normalisation."""

    def test_adds_https_scheme(self):
        assert validate_url("example.com") == "https://example.com"

    def test_preserves_http(self):
        assert validate_url("http://example.com") == "http://example.com"

    def test_preserves_https(self):
        assert validate_url("https://example.com/path") == "https://example.com/path"

    def test_rejects_empty_netloc(self):
        import argparse
        with pytest.raises(argparse.ArgumentTypeError):
            validate_url("https://")

    def test_url_with_path(self):
        assert validate_url("example.com/path") == "https://example.com/path"

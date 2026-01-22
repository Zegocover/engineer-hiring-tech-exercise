import pytest
from src.utils import normalize_url, is_same_domain

def test_normalize_url():
    base = "https://example.com/foo/"
    assert normalize_url(base, "bar") == "https://example.com/foo/bar"
    assert normalize_url(base, "/bar") == "https://example.com/bar"
    assert normalize_url(base, "https://example.com/baz") == "https://example.com/baz"
    assert normalize_url(base, "bar#fragment") == "https://example.com/foo/bar"

def test_is_same_domain():
    base = "https://example.com"
    assert is_same_domain(base, "https://example.com/foo") is True
    assert is_same_domain(base, "http://example.com/bar") is True
    assert is_same_domain(base, "https://sub.example.com") is False
    assert is_same_domain(base, "https://google.com") is False
    assert is_same_domain(base, "/relative") is False # Relative URLs don't have netloc

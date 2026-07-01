"""Shared fixtures for crawler tests."""

import pytest


@pytest.fixture
def sample_html() -> str:
    """Simple HTML page with various link types for testing."""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Test Page</title></head>
    <body>
        <a href="/about">About</a>
        <a href="/contact">Contact</a>
        <a href="https://example.com/products">Products</a>
        <a href="https://other.com/external">External</a>
        <a href="https://sub.example.com/subdomain">Subdomain</a>
        <a href="mailto:test@example.com">Email</a>
        <a href="tel:+1234567890">Phone</a>
        <a href="javascript:void(0)">JS Link</a>
        <a href="#section">Anchor</a>
        <a href="">Empty</a>
        <a href="  /whitespace  ">Whitespace</a>
        <a href="relative/path">Relative</a>
        <a href="https://example.com/page#fragment">With Fragment</a>
        <a href="https://example.com/page/">Trailing Slash</a>
        <a href="ftp://example.com/file">FTP</a>
    </body>
    </html>
    """


@pytest.fixture
def base_url() -> str:
    return "https://example.com"


@pytest.fixture
def base_domain() -> str:
    return "example.com"

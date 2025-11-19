import pytest
from urllib.parse import urljoin, urlparse, parse_qs
from web_crawler import WebCrawler



def test_is_same_host():
    c = WebCrawler('https://example.com')

    # same host (exact match)
    assert c._is_same_host('https://example.com/path')

    # same host with explicit port still matches
    assert c._is_same_host('https://example.com:8080/other')

    # different domain should be False
    assert not c._is_same_host('https://other.com/')

    # subdomain is considered different (strict hostname equality)
    assert not c._is_same_host('https://sub.example.com/page')

    # mailto and non-http schemes return False
    assert not c._is_same_host('mailto:me@example.com')

    # falsy input returns False
    assert not c._is_same_host(None)


def test_normalisation_strip_tracking():
    c = WebCrawler("https://example.com") # strip_tracking_params=True by default
    url = "https://example.com/path?utm_source=x&b=1#frag"
    assert c._normalise(url) == "https://example.com/path?b=1"


def test_extract_links_filters_mailto_and_tel():
    c = WebCrawler('https://example.com')
    html = '<a href="https://example.com/p">p</a><a href="/p">p</a><a href="mailto:me@example.com">m</a><a href="tel:+123">t</a>'
    links = c._extract_links('https://example.com/', html)

    assert 'https://example.com/p' in links
    assert links.count('https://example.com/p') == 1 # deduped
    assert all(not l.startswith('mailto:') and not l.startswith('tel:') for l in links)


def test_extract_links_respects_base_tag():
    c = WebCrawler('https://example.com')
    html = '<base href="/sub/" /><a href="p.html">p</a>'
    links = c._extract_links('https://example.com/page', html)
    assert 'https://example.com/sub/p.html' in links


def test_extract_canonical():
    c = WebCrawler('https://example.com')
    html = '<link rel="canonical" href="https://cdn.example.org/canonical.html" />'
    res = c._extract_canonical(html, 'https://example.com/page')
    assert res == 'https://cdn.example.org/canonical.html'


def test_extract_canonical_respects_base_tag():
    c = WebCrawler('https://example.com')
    html = '<base href="/sub/" /><link rel="canonical" href="canonical.html" />'
    res = c._extract_canonical(html, 'https://example.com/page')
    assert res == 'https://example.com/sub/canonical.html'
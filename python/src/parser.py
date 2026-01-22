"""
Parser Module
-------------

This module takes raw HTML content and extracts links.
It uses BeautifulSoup with lxml for high-performance parsing.
"""
from bs4 import BeautifulSoup
from typing import Set
from .utils import normalize_url, is_same_domain

def extract_links(html_content: str, base_url: str) -> Set[str]:
    """
    Extracts all valid links from the HTML content that belong to the same domain.
    Returns a set of normalized, absolute URLs.
    """
    links = set()
    try:
        soup = BeautifulSoup(html_content, 'lxml')
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            normalized = normalize_url(base_url, href)
            
            # Filter out non-http/https schemes (e.g., mailto:, tel:, javascript:)
            if not normalized.startswith(('http://', 'https://')):
                continue
                
            if is_same_domain(base_url, normalized):
                links.add(normalized)
    except Exception as e:
        # In a real crawler, we might log this error
        pass
        
    return links

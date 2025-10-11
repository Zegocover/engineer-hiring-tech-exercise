from typing import List
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup

from interfaces.i_link_parser import ILinkParser

class LinkParser(ILinkParser):
    
    def __init__(self, domain: str):
        self.domain = domain

    def extract_links(self, html: str, current_url: str) -> List[str]:
        
        # Parse the HTML content into a tree
        soup = BeautifulSoup(html, "lxml")
        
        # Find all anchor tags (<a>) that have href attributes
        anchors = soup.find_all("a", href=True)
        
        # Create empty list to store the links we want to keep
        links = []

        for a in anchors:
            # Extract the href attribute value 
            href = a.get("href").strip()
            
            if not href:
                continue
            
            # Convert relative URLs to absolute URLs
            # - "/about" becomes "https://example.com/about"  
            abs_link = urljoin(current_url, href)
            
            # Parse the absolute URL
            parsed = urlparse(abs_link)
            
            # Only keep links that are on the same domain
            if parsed.netloc == self.domain:
                # Remove URL fragments (the #section part)
                clean_link = abs_link.split("#")[0]
            
                links.append(clean_link)

        # Remove duplicates and return final list
        return list(set(links))
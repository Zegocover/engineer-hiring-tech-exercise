from typing import Set
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from bs4.element import AttributeValueList, Tag


class Parser:
    def parse(self, base_url: str, html_content: str) -> Set[str]:
        soup = BeautifulSoup(html_content, "html.parser")
        links: Set[str] = set()
        for link in soup.find_all("a", href=True):
            if not isinstance(link, Tag):
                continue

            href_value = link.get("href")
            if href_value is None:
                continue

            if isinstance(href_value, str):
                links.add(urljoin(base_url, href_value))
                continue

            if isinstance(href_value, AttributeValueList) and href_value:
                links.add(urljoin(base_url, str(href_value[0])))

        return links

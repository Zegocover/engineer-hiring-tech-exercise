from re import Pattern
from typing import Callable, Dict, Iterable, List, Set, Union
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag
from bs4.element import AttributeValueList


class Parser:
    def _extract_links_from_tags(
        self, soup: BeautifulSoup, tag_name: str, attribute_name: str
    ) -> List[str]:
        links: List[str] = []
        attrs: Dict[
            str,
            Union[
                Callable[[str], bool],
                Iterable[Union[Callable[[str], bool], Pattern[str], bool, bytes, str]],
                Pattern[str],
                bool,
                bytes,
                str,
            ],
        ] = {attribute_name: True}
        for tag in soup.find_all(tag_name, attrs):
            if not isinstance(tag, Tag):
                continue
            attribute_value = tag.get(attribute_name)
            if isinstance(attribute_value, str):
                links.append(attribute_value)
                continue
            if isinstance(attribute_value, AttributeValueList) and attribute_value:
                links.append(str(attribute_value[0]))
        return links

    def parse(self, base_url: str, html_content: str) -> Set[str]:
        soup = BeautifulSoup(html_content, "html.parser")
        found_links: Set[str] = set()

        href_links = self._extract_links_from_tags(soup, "a", "href")
        for link in href_links:
            found_links.add(urljoin(base_url, link))

        src_links = self._extract_links_from_tags(soup, "img", "src")
        for link in src_links:
            found_links.add(urljoin(base_url, link))

        stylesheet_links = self._extract_links_from_tags(soup, "link", "href")
        for link in stylesheet_links:
            if not soup.find("link", href=link, rel="stylesheet"):
                continue
            found_links.add(urljoin(base_url, link))

        return found_links

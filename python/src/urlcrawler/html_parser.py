import logging
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

_LOG = logging.getLogger(__name__)


class HtmlParser:
    """
    Class that is responsible of Parsing an HTML request
    """

    def find_urls(self, main_url: str, response: str):
        """
        Returns all the urls found in <a> elements in a html response.
        """
        # NOTE: It's not clear in the requirements if we also need to find
        # URLs embedded as text content on the response, or URLS pointing to
        # static assets.
        # Given that we are writing a crawler, I implemented the most logical scenario.
        # But if the requirement changes, this class is responsible of finding URLs any other way.
        # Thinking regex or a querying for other elements depending on the requirements.
        links = []
        soup = BeautifulSoup(response, "html.parser")
        for link_tag in soup.find_all("a", href=True):
            href = link_tag["href"].strip()
            if not href or href.startswith(
                ("#", "javascript:", "mailto:", "callto:", "tel:")
            ):
                _LOG.debug(f"Skipping: {href} invalid href.")
                continue
            absolute_url = self.__get_absolute_url(main_url, href)
            parsed_url = urlparse(absolute_url)
            if parsed_url.scheme not in ["http", "https"]:
                _LOG.debug(f"Skipping: {absolute_url} invalid scheme")
                continue
            links.append(absolute_url)
        return links

    def __get_absolute_url(self, main_url: str, url: str):
        """Converts relative URLs to absolute URLs"""
        main_domain = urlparse(main_url).netloc.lower()
        if url.startswith(main_domain):
            # Fixes condition where the URL does not start with a scheme
            # E.G. href="zego.com/onboarding/scooter-motorbike-delivery/requirements"
            return urljoin(main_url, url.replace(main_domain, main_url, 1))
        return urljoin(main_url, url)

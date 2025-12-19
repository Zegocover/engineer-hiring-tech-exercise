import logging
import requests
from typing import Optional, Tuple

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

HEADERS = {"User-Agent": "Zego-Crawler/1.0 (+https://zego.com/careers)"}


def fetch_url(url: str, timeout: int = 10) -> Tuple[str, Optional[str]]:
    """
    Fetch a URL and return (url, content) or (url, None) on failure.
    """
    try:
        response = requests.get(
            url, headers=HEADERS, timeout=timeout, allow_redirects=True
        )
        if response.status_code == 200:
            return url, response.text
        else:
            logging.warning(f"HTTP {response.status_code} for {url}")
    except requests.RequestException as e:
        logging.error(f"Failed to fetch {url}: {e}")

    return url, None

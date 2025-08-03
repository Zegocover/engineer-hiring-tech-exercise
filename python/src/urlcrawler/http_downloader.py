import requests
import logging
import os.path
import hashlib

_LOG = logging.getLogger(__name__)


class HttpDownloader:
    """Class in charge of downloading urls
    use_cache: true if it's okay to use the cached version of the file.
    """

    def __init__(self, use_cache=False):
        # NOTE: Imagine an scenario where the processing crashes in the middle of a crawl
        # We this stateless approach you need to start over and download everything again.
        # use_cache enables the consumer to use a cached version of the files assuming there are no data freshness concerns.
        #
        # This hypothetical example showcase a use case where having a separate class
        # is actually useful instead of hardcoding this logic the main class
        if use_cache:
            _LOG.info(f"HttpDownloader using cache")
        self.use_cache = use_cache
        os.makedirs("./cache", exist_ok=True)

    def get(self, url: str) -> str:
        filename = f"./cache/{hashlib.md5(url.encode("utf-8")).hexdigest()}.txt"
        if self.use_cache and os.path.exists(filename):
            _LOG.debug(f"Response found in cache: {url} {filename}")
            with open(filename, encoding="utf-8") as f:
                return f.read()
        response = requests.get(url)
        response.raise_for_status()
        if self.use_cache:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(response.text)
        return response.text

import requests
import urllib.parse
from queue import Queue
from threading import Lock

# Singleton pattern to store the shared resources
class Config:
    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(Config, cls).__new__(cls)
            cls.instance.session = requests.Session()
            cls.instance.visited_urls = set()
            cls.instance.queue = Queue()
            cls.instance.lock = Lock()
        return cls.instance

    def get_domain(cls, url: str) -> str:
        cls.instance.domain = urllib.parse.urlparse(url).netloc.split(":")[0]
        cls.instance.scheme = urllib.parse.urlparse(url).scheme
        return cls.instance.domain, cls.instance.scheme

    def validate_url_domain(self, url: str) -> bool:
        url_domain = urllib.parse.urlparse(url).netloc.split(":")[0]
        if url_domain != self.domain:
            return False
        return True
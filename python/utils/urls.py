from urllib.parse import urlparse
from tldextract import extract

def clean_url(url: str) -> str:
    url = urlparse(url)._replace(fragment="", query="").geturl()
    if url.endswith("/"):
        url = url[:-1]
    return url.replace("www.", "")

def is_relative_url(url: str) -> bool:
    return url.startswith("/")

def within_subdomain(url: str, base_url: str) -> bool:
    extracted_url = extract(url)
    scheme = urlparse(url).scheme
    extracted_base = extract(base_url)
    is_within_domain = extracted_url.fqdn == extracted_base.fqdn
    return is_within_domain and scheme in ["http", "https", ""]
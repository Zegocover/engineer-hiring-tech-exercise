from _given_steps import *
from _then_steps import *
from _when_steps import *
from pytest_bdd import scenario


@scenario(
    "features/cli_application.feature", "Crawl a local website and list internal links"
)
def test_crawl_a_local_website_and_list_internal_links():
    pass

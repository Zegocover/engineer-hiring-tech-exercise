from pytest_bdd import scenario


@scenario(
    "features/cli_application.feature", "Crawl a local website and list internal links"
)
def test_crawl_a_local_website_and_list_internal_links():
    pass

import re

from pytest_bdd import then


@then(
    "I should see a report of the URLs of each page and the links found on them within the same domain"
)
def assert_printed_url_report(website, crawler_report):
    expected = (
        "\n".join(
            [
                f"200 {website}",
                f" - {website}/kungfu.gif",
                f" - {website}/level1/",
                f" - {website}/style.css",
                f" - http://www.example.com",
                f"200 {website}/level1/",
                f" - {website}/empty_page.html",
                f" - {website}/level2/",
                f"404 {website}/level2/",
                f" - {website}/report.html",
                f"404 {website}/style.css",
                f" - {website}/report.html",
                f"200 {website}/kungfu.gif",
                f" * No links *",
                f"200 {website}/report.html",
                f" * No links *",
                f"200 {website}/empty_page.html",
                " * No links *",
            ]
        )
        + "\n"
    )
    assert bytes.decode(crawler_report) == expected


@then("no external site was visited")
def assert_no_external_urls_visited():
    with open("crawlspace.log", "r") as logfile:
        for line in logfile:
            assert not re.search(r"\sGET http:\/\/www.example.com\s", line, flags=0)

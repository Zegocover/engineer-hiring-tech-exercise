from pytest_bdd import then


@then(
    "I should see a report of the URLs of each page and the links found on them within the same domain"
)
def assert_printed_url_report(website, crawler_report):
    expected = (
        "\n".join(
            [
                f"200 {website}",
                f" - {website}/level1/",
                f"200 {website}/level1/",
                f" - {website}/empty_page.html",
                f" - {website}/level2/",
                f"404 {website}/level2/",
                f" - {website}/report.html",
                f"200 {website}/report.html",
                f" * No links *",
                f"200 {website}/empty_page.html",
                " * No links *",
            ]
        )
        + "\n"
    )
    assert bytes.decode(crawler_report) == expected

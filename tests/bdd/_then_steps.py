from pytest_bdd import then


@then(
    "I should see a report of the URLs of each page and the links found on them within the same domain"
)
def assert_printed_url_report(website, crawler_report):
    expected = (
        "\n".join(
            [
                f"200 {website}",
                f" - {website}/empty-page",
                f"200 {website}/empty-page",
                f" * No links *",
            ]
        )
        + "\n"
    )
    assert bytes.decode(crawler_report) == expected

from pytest_bdd import then


@then(
    "I should see a report of the URLs of each page and the links found on them within the same domain"
)
def assert_printed_url_report():
    pass

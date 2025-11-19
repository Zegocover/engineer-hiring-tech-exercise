import unittest

from web_crawler.url import URL


class TestURLInitAndNormalization(unittest.TestCase):
    def test_initial_removes_fragment(self):
        url = URL("https://example.com/page.html#section")
        self.assertEqual("https://example.com/page.html", str(url))

    def test_initial_strips_trailing_slash(self):
        url = URL("https://example.com/path/")
        self.assertEqual("https://example.com/path", str(url))

    def test_initial_removes_fragment_then_trailing_slash(self):
        url = URL("https://example.com/path/#section")
        self.assertEqual("https://example.com/path", str(url))

    def test_initial_no_fragment_or_trailing_slash_unchanged(self):
        url = URL("https://example.com/path")
        self.assertEqual("https://example.com/path", str(url))


class TestEqualityAndHash(unittest.TestCase):
    def test_equality_based_on_normalized_string(self):
        url1 = URL("https://example.com/path/#section")
        url2 = URL("https://example.com/path/")
        self.assertEqual(url1, url2)

    def test_equality_with_different_urls(self):
        url1 = URL("https://example.com/path1")
        url2 = URL("https://example.com/path2")
        self.assertNotEqual(url1, url2)

    def test_hash_consistent_with_equality(self):
        url1 = URL("https://example.com/path/#section")
        url2 = URL("https://example.com/path")
        self.assertEqual(hash(url1), hash(url2))
        url_set = {url1}
        self.assertIn(url2, url_set)


class TestGetDomain(unittest.TestCase):
    def test_get_domain_simple(self):
        url = URL("https://example.com/a/path/index.html")
        self.assertEqual("https://example.com", url.get_domain())

    def test_get_domain_with_port_and_query_and_fragment(self):
        url = URL("http://example.com/a/b?x=1#fragment")
        # fragment is removed on init
        self.assertEqual("http://example.com/a/b?x=1", str(url))
        self.assertEqual("http://example.com", url.get_domain())

    def test_get_domain_for_root_url(self):
        url = URL("https://example.com/")
        self.assertEqual("https://example.com", url.get_domain())


class TestStripLastSlash(unittest.TestCase):
    def test_strip_last_slash_removes_when_present(self):
        self.assertEqual(
            "https://example.com/path",
            URL.strip_last_slash("https://example.com/path/"),
        )

    def test_strip_last_slash_no_change_when_absent(self):
        self.assertEqual(
            "https://example.com/path",
            URL.strip_last_slash("https://example.com/path"),
        )

    def test_strip_last_slash_root_url(self):
        self.assertEqual(
            "https://example.com",
            URL.strip_last_slash("https://example.com/"),
        )


class TestRemoveUrlFragment(unittest.TestCase):
    def test_remove_url_fragment_when_present(self):
        self.assertEqual(
            "https://example.com/page.html",
            URL.remove_url_fragment("https://example.com/page.html#section"),
        )

    def test_remove_url_fragment_without_fragment(self):
        self.assertEqual(
            "https://example.com/page.html",
            URL.remove_url_fragment("https://example.com/page.html"),
        )


class TestMakeAbsolute(unittest.TestCase):
    def test_make_absolute_from_relative_path(self):
        url = URL("./page.html")
        abs_url = url.make_absolute(URL("https://example.com"))
        self.assertIsInstance(abs_url, URL)
        self.assertEqual("https://example.com/page.html", str(abs_url))

    def test_make_absolute_does_not_override_existing_domain(self):
        url = URL("https://a.com/page.html")
        abs_url = url.make_absolute(URL("https://b.com"))
        self.assertEqual("https://a.com/page.html", str(abs_url))

    def test_make_absolute_with_same_domain(self):
        url = URL("https://example.com/path/page.html")
        abs_url = url.make_absolute(URL("https://example.com"))
        self.assertEqual("https://example.com/path/page.html", str(abs_url))

    def test_make_absolute_handles_trailing_slash_in_domain(self):
        url = URL("sub/page")
        abs_url = url.make_absolute(URL("https://example.com/"))
        self.assertEqual("https://example.com/sub/page", str(abs_url))


if __name__ == "__main__":
    unittest.main()

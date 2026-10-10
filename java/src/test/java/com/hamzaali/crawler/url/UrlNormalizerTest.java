package com.hamzaali.crawler.url;

import static org.assertj.core.api.Assertions.assertThat;

import java.net.URI;
import java.util.Optional;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.junit.jupiter.params.provider.NullAndEmptySource;
import org.junit.jupiter.params.provider.ValueSource;

class UrlNormalizerTest {

    @Nested
    class Normalize {

        @ParameterizedTest(name = "{0} -> {1}")
        @CsvSource({
            "HTTP://Example.COM/About, http://example.com/About",
            "http://example.com, http://example.com/",
            "http://127.0.0.1:57296, http://127.0.0.1:57296/",
            "http://example.com:80/a, http://example.com/a",
            "https://example.com:443/a, https://example.com/a",
            "http://example.com:443/a, http://example.com:443/a",
            "https://example.com:8080/a, https://example.com:8080/a",
            "http://example.com/a#section, http://example.com/a",
            "http://example.com/a/, http://example.com/a/",
            "http://example.com/a/./b/../c, http://example.com/a/c",
            "http://example.com/s?q=1&b=2, http://example.com/s?q=1&b=2",
            "http://example.com/a%2Fb, http://example.com/a%2Fb",
            "http://example.com/a b, http://example.com/a%20b",
            "http://example.com/café, http://example.com/caf%C3%A9",
            "http://example.com/caf%C3%A9, http://example.com/caf%C3%A9",
            "http://example.com/100%, http://example.com/100%25",
            "http://[::1]:8080/a, http://[::1]:8080/a",
            "http://sub.127.0.0.1:60991/page, http://sub.127.0.0.1:60991/page",
        })
        void shouldCanonicalizeUrl(String url, String expected) {
            Optional<URI> result = UrlNormalizer.normalize(url);

            assertThat(result).map(URI::toString).hasValue(expected);
        }

        @ParameterizedTest
        @NullAndEmptySource
        @ValueSource(
                strings = {
                    "   ",
                    "mailto:test@example.com",
                    "tel:+1234567890",
                    "javascript:void(0)",
                    "data:text/plain,hello",
                    "ftp://example.com/file",
                    "http://",
                    "/relative/path",
                })
        void shouldRejectUrlWhenItIsNotCrawlable(String url) {
            Optional<URI> result = UrlNormalizer.normalize(url);

            assertThat(result).isEmpty();
        }

        @Test
        void shouldProduceEqualUrisWhenSamePageIsSpelledDifferently() {
            String spelledUnusually = "HTTP://Example.com:80/a#top";
            String spelledCanonically = "http://example.com/a";

            Optional<URI> unusual = UrlNormalizer.normalize(spelledUnusually);
            Optional<URI> canonical = UrlNormalizer.normalize(spelledCanonically);

            assertThat(unusual).isEqualTo(canonical);
        }

        @Test
        void shouldDropCredentialsWhenUrlContainsUserInfo() {
            Optional<URI> result = UrlNormalizer.normalize("https://user:secret@example.com/private");

            assertThat(result).map(URI::toString).hasValue("https://example.com/private");
        }
    }

    @Nested
    class Resolve {

        private final URI page = URI.create("http://example.com/dir/page?old=1");

        @ParameterizedTest(name = "{0} -> {1}")
        @CsvSource({
            "/about, http://example.com/about",
            "other, http://example.com/dir/other",
            "./other, http://example.com/dir/other",
            "../up, http://example.com/up",
            "../../../too-far, http://example.com/too-far",
            "?q=1, http://example.com/dir/page?q=1",
            "//other.com/x, http://other.com/x",
            "https://sub.example.com/p, https://sub.example.com/p",
            "/a#fragment, http://example.com/a",
            "'  /padded  ', http://example.com/padded",
        })
        void shouldResolveLinkRelativeToPage(String href, String expected) {
            Optional<URI> result = UrlNormalizer.resolve(page, href);

            assertThat(result).map(URI::toString).hasValue(expected);
        }

        @Test
        void shouldResolveLinkWhenPageHasEmptyPath() {
            URI pageWithoutPath = URI.create("http://example.com");

            Optional<URI> result = UrlNormalizer.resolve(pageWithoutPath, "foo");

            assertThat(result).map(URI::toString).hasValue("http://example.com/foo");
        }

        @Test
        void shouldIgnoreTabsAndNewlinesWhenTheyAppearInsideLink() {
            Optional<URI> result = UrlNormalizer.resolve(page, "\t/con\ntact\r\n");

            assertThat(result).map(URI::toString).hasValue("http://example.com/contact");
        }

        @ParameterizedTest
        @NullAndEmptySource
        @ValueSource(strings = {"   ", "#", "#top", "mailto:test@example.com", "javascript:void(0)", "tel:123"})
        void shouldIgnoreLinkWhenItIsNotCrawlable(String href) {
            Optional<URI> result = UrlNormalizer.resolve(page, href);

            assertThat(result).isEmpty();
        }
    }
}

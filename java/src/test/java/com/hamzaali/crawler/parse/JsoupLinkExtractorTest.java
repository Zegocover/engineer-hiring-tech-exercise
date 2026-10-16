package com.hamzaali.crawler.parse;

import static org.assertj.core.api.Assertions.assertThat;

import java.net.URI;
import java.util.Set;
import org.junit.jupiter.api.Test;

class JsoupLinkExtractorTest {

    private static final URI PAGE = URI.create("https://example.com/catalog/index");

    private final JsoupLinkExtractor extractor = new JsoupLinkExtractor();

    @Test
    void shouldExtractAndResolveHttpLinks() {
        String html = """
                <a href="/about">Root relative</a>
                <a href="item">Path relative</a>
                <a href="https://example.com/contact">Absolute</a>
                <a href="https://other.example/news">External</a>
                <a href="https://sub.example.com/help">Subdomain</a>
                <a href="http://sub.127.0.0.1:60991/page">Literal subdomain</a>
                """;

        Set<URI> links = extractor.extractLinks(PAGE, html);

        assertThat(links)
                .containsExactlyInAnyOrder(
                        URI.create("https://example.com/about"),
                        URI.create("https://example.com/catalog/item"),
                        URI.create("https://example.com/contact"),
                        URI.create("https://other.example/news"),
                        URI.create("https://sub.example.com/help"),
                        URI.create("http://sub.127.0.0.1:60991/page"));
    }

    @Test
    void shouldExcludeLinksThatCannotBeCrawled() {
        String html = """
                <a href="">Empty</a>
                <a href="#details">Fragment</a>
                <a href="mailto:help@example.com">Email</a>
                <a href="tel:0123456789">Telephone</a>
                <a href="javascript:void(0)">JavaScript</a>
                <a href="ftp://example.com/file">FTP</a>
                """;

        Set<URI> links = extractor.extractLinks(PAGE, html);

        assertThat(links).isEmpty();
    }

    @Test
    void shouldRemoveDuplicateCanonicalUrls() {
        String html = """
                <a href="https://EXAMPLE.com:443/about#team">First</a>
                <a href="/about">Second</a>
                <a href="/about">Third</a>
                """;

        Set<URI> links = extractor.extractLinks(PAGE, html);

        assertThat(links).containsExactly(URI.create("https://example.com/about"));
    }

    @Test
    void shouldResolveLinksAgainstFirstBaseElement() {
        String html = """
                <base href="https://assets.example/content/">
                <base href="https://ignored.example/">
                <a href="guide">Guide</a>
                """;

        Set<URI> links = extractor.extractLinks(PAGE, html);

        assertThat(links).containsExactly(URI.create("https://assets.example/content/guide"));
    }

    @Test
    void shouldUsePageWhenBaseElementIsInvalid() {
        String html = """
                <base href="mailto:help@example.com">
                <a href="guide">Guide</a>
                """;

        Set<URI> links = extractor.extractLinks(PAGE, html);

        assertThat(links).containsExactly(URI.create("https://example.com/catalog/guide"));
    }

    @Test
    void shouldDecodeHtmlEntitiesInLinks() {
        String html = """
                <a href="/search?a=1&amp;b=2">Search</a>
                """;

        Set<URI> links = extractor.extractLinks(PAGE, html);

        assertThat(links).containsExactly(URI.create("https://example.com/search?a=1&b=2"));
    }

    @Test
    void shouldRecoverLinksFromMalformedHtml() {
        String html = """
                <html><body><a href="/first">First<a href="/second">Second
                """;

        Set<URI> links = extractor.extractLinks(PAGE, html);

        assertThat(links)
                .containsExactlyInAnyOrder(
                        URI.create("https://example.com/first"), URI.create("https://example.com/second"));
    }

    @Test
    void shouldReturnEmptySetWhenHtmlIsMissing() {
        assertThat(extractor.extractLinks(PAGE, null)).isEmpty();
    }

    @Test
    void shouldReturnEmptySetWhenPageIsMissing() {
        String html = """
                <a href="/about">About</a>
                """;

        assertThat(extractor.extractLinks(null, html)).isEmpty();
    }
}

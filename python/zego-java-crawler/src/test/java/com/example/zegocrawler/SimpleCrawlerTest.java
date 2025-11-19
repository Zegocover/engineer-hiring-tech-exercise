package com.example.zegocrawler;

import static org.junit.jupiter.api.Assertions.*;

import java.net.URI;
import java.net.URISyntaxException;
import java.util.Set;
import org.junit.jupiter.api.Test;

public class SimpleCrawlerTest {

    @Test
    void normalizeResolvesRelativeAndStripsFragment() throws URISyntaxException {
        String base = "https://example.com/path/index.html";
        String href = "../about#team";
        String normalized = SimpleCrawler.normalize(base, href);
        assertEquals("https://example.com/about", normalized);
    }

    @Test
    void normalizeIgnoresMailtoAndJavascript() {
        String base = "https://example.com/";
        assertNull(SimpleCrawler.normalize(base, "mailto:someone@example.com"));
        assertNull(SimpleCrawler.normalize(base, "javascript:alert('hi')"));
    }

    @Test
    void normalizeRejectsNonHttpSchemes() {
        String base = "https://example.com/";
        assertNull(SimpleCrawler.normalize(base, "ftp://example.com/file.txt"));
    }

    @Test
    void sameExactHostAcceptsExactDomainOnly() {
        SimpleCrawler crawler = new SimpleCrawler("https://example.com", 1, 10,
            java.time.Duration.ofSeconds(5), "UA");
        assertTrue(crawler.sameExactHost("https://example.com/page"));
        assertFalse(crawler.sameExactHost("https://www.example.com/page"));
        assertFalse(crawler.sameExactHost("https://sub.example.com/page"));
        assertFalse(crawler.sameExactHost("https://other.com/page"));
    }

    @Test
    void extractLinksFindsAnchors() {
        String base = "https://example.com/";
        String html = "<html><body>" +
            "<a href=\"/about\">About</a>" +
            "<a href=\"https://example.com/contact#fragment\">Contact</a>" +
            "<a href=\"mailto:test@example.com\">Mail</a>" +
            "</body></html>";
        Set<String> links = SimpleCrawler.extractLinks(base, html);
        assertEquals(2, links.size());
        assertTrue(links.contains("https://example.com/about"));
        assertTrue(links.contains("https://example.com/contact"));
    }

    @Test
    void isHttpishWorksForHttpAndHttps() throws URISyntaxException {
        assertTrue(SimpleCrawler.isHttpish(new URI("http://example.com")));
        assertTrue(SimpleCrawler.isHttpish(new URI("https://example.com")));
        assertFalse(SimpleCrawler.isHttpish(new URI("ftp://example.com")));
    }
}

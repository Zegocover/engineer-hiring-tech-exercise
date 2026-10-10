package com.hamzaali.crawler.output;

import static org.assertj.core.api.Assertions.assertThat;

import java.io.ByteArrayOutputStream;
import java.io.PrintStream;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.util.Set;
import org.junit.jupiter.api.Test;

class ConsoleCrawlListenerTest {

    private static final URI HOME = URI.create("https://example.com/");
    private static final URI ABOUT = URI.create("https://example.com/about");
    private static final URI EXTERNAL = URI.create("https://other.example/news");

    @Test
    void shouldPrintPageAndSortedLinks() {
        ByteArrayOutputStream buffer = new ByteArrayOutputStream();
        ConsoleCrawlListener listener = new ConsoleCrawlListener(new PrintStream(buffer, true, StandardCharsets.UTF_8));

        listener.onPage(new PageReport(HOME, Set.of(EXTERNAL, ABOUT)));

        assertThat(buffer.toString(StandardCharsets.UTF_8)).isEqualTo("""
                        https://example.com/
                          https://example.com/about
                          https://other.example/news
                        """);
    }

    @Test
    void shouldPrintPageWhenNoLinksAreFound() {
        ByteArrayOutputStream buffer = new ByteArrayOutputStream();
        ConsoleCrawlListener listener = new ConsoleCrawlListener(new PrintStream(buffer, true, StandardCharsets.UTF_8));

        listener.onPage(new PageReport(HOME, Set.of()));

        assertThat(buffer.toString(StandardCharsets.UTF_8)).isEqualTo("https://example.com/\n");
    }

    @Test
    void shouldKeepLinesFromOnePageTogether() {
        ByteArrayOutputStream buffer = new ByteArrayOutputStream();
        ConsoleCrawlListener listener = new ConsoleCrawlListener(new PrintStream(buffer, true, StandardCharsets.UTF_8));
        URI contact = URI.create("https://example.com/contact");

        listener.onPage(new PageReport(HOME, Set.of(ABOUT)));
        listener.onPage(new PageReport(ABOUT, Set.of(contact)));

        assertThat(buffer.toString(StandardCharsets.UTF_8)).isEqualTo("""
                        https://example.com/
                          https://example.com/about
                        https://example.com/about
                          https://example.com/contact
                        """);
    }
}

package com.hamzaali.crawler.output;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatIllegalArgumentException;

import java.net.URI;
import java.util.HashSet;
import java.util.Set;
import org.junit.jupiter.api.Test;

class PageReportTest {

    private static final URI HOME = URI.create("https://example.com/");

    @Test
    void shouldCopyLinksSoCallersCannotChangeTheReport() {
        Set<URI> links = new HashSet<>();
        links.add(URI.create("https://example.com/about"));
        PageReport report = new PageReport(HOME, links);

        links.clear();

        assertThat(report.links()).containsExactly(URI.create("https://example.com/about"));
    }

    @Test
    void shouldTreatMissingLinksAsEmpty() {
        PageReport report = new PageReport(HOME, null);

        assertThat(report.links()).isEmpty();
    }

    @Test
    void shouldRejectMissingPage() {
        assertThatIllegalArgumentException().isThrownBy(() -> new PageReport(null, Set.of()));
    }
}

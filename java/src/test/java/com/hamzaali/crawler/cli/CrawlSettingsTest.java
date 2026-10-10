package com.hamzaali.crawler.cli;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatIllegalArgumentException;

import java.net.URI;
import java.time.Duration;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

class CrawlSettingsTest {

    @Test
    void shouldAddHttpsWhenSchemeIsMissing() {
        assertThat(CrawlSettings.parseSeed("example.com/about")).isEqualTo(URI.create("https://example.com/about"));
    }

    @Test
    void shouldKeepHttpWhenSchemeIsPresent() {
        assertThat(CrawlSettings.parseSeed("http://example.com")).isEqualTo(URI.create("http://example.com/"));
    }

    @ParameterizedTest
    @ValueSource(strings = {"", "   ", "://missing-host", "ftp://example.com"})
    void shouldRejectSeedWhenItIsNotCrawlable(String value) {
        assertThatIllegalArgumentException().isThrownBy(() -> CrawlSettings.parseSeed(value));
    }

    @Test
    void shouldRejectConcurrencyBelowOne() {
        assertThatIllegalArgumentException().isThrownBy(() -> settings(0, Duration.ofSeconds(1), 2, 3, 100, "agent"));
    }

    private static CrawlSettings settings(
            int concurrency, Duration timeout, int maxDepth, int maxRedirects, int maxBytes, String userAgent) {
        return new CrawlSettings(
                URI.create("https://example.com/"), concurrency, timeout, maxDepth, maxRedirects, maxBytes, userAgent);
    }
}

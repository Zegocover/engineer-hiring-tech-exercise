package com.hamzaali.crawler.fetch;

import static org.assertj.core.api.Assertions.assertThatIllegalArgumentException;

import java.time.Duration;
import org.junit.jupiter.api.Test;

class HttpFetcherConfigTest {

    private static final Duration TIMEOUT = Duration.ofSeconds(10);
    private static final String USER_AGENT = "ZegoCrawler/0.1";

    @Test
    void shouldRejectTimeoutWhenItIsNotPositive() {
        assertThatIllegalArgumentException()
                .isThrownBy(() -> new HttpFetcherConfig(Duration.ZERO, 5, 1_000, USER_AGENT));
    }

    @Test
    void shouldRejectRedirectLimitWhenItIsNegative() {
        assertThatIllegalArgumentException().isThrownBy(() -> new HttpFetcherConfig(TIMEOUT, -1, 1_000, USER_AGENT));
    }

    @Test
    void shouldRejectResponseLimitWhenItIsNotPositive() {
        assertThatIllegalArgumentException().isThrownBy(() -> new HttpFetcherConfig(TIMEOUT, 5, 0, USER_AGENT));
    }

    @Test
    void shouldRejectResponseLimitWhenItWouldOverflowReadBuffer() {
        assertThatIllegalArgumentException()
                .isThrownBy(() -> new HttpFetcherConfig(TIMEOUT, 5, Integer.MAX_VALUE, USER_AGENT));
    }

    @Test
    void shouldRejectUserAgentWhenItIsBlank() {
        assertThatIllegalArgumentException().isThrownBy(() -> new HttpFetcherConfig(TIMEOUT, 5, 1_000, " "));
    }
}

package com.hamzaali.crawler.fetch;

import java.time.Duration;
import java.util.Objects;

public record HttpFetcherConfig(Duration requestTimeout, int maxRedirects, int maxResponseBytes, String userAgent) {

    public HttpFetcherConfig {
        Objects.requireNonNull(requestTimeout, "requestTimeout must not be null");
        Objects.requireNonNull(userAgent, "userAgent must not be null");

        if (requestTimeout.isZero() || requestTimeout.isNegative()) {
            throw new IllegalArgumentException("requestTimeout must be positive");
        }
        if (maxRedirects < 0) {
            throw new IllegalArgumentException("maxRedirects must not be negative");
        }
        if (maxResponseBytes <= 0 || maxResponseBytes == Integer.MAX_VALUE) {
            throw new IllegalArgumentException("maxResponseBytes must be between 1 and Integer.MAX_VALUE - 1");
        }
        if (userAgent.isBlank()) {
            throw new IllegalArgumentException("userAgent must not be blank");
        }
    }
}

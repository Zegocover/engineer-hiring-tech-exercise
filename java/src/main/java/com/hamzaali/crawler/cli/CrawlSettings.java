package com.hamzaali.crawler.cli;

import com.hamzaali.crawler.url.UrlNormalizer;
import java.net.URI;
import java.time.Duration;
import java.util.Optional;

public record CrawlSettings(
        URI seed,
        int concurrency,
        Duration requestTimeout,
        int maxDepth,
        int maxRedirects,
        int maxResponseBytes,
        String userAgent) {

    public CrawlSettings {
        seed = Optional.ofNullable(seed)
                .flatMap(uri -> UrlNormalizer.normalize(uri.toString()))
                .orElseThrow(() -> new IllegalArgumentException("seed must be an absolute HTTP or HTTPS URL"));
        if (concurrency < 1) {
            throw new IllegalArgumentException("concurrency must be at least 1");
        }
        requestTimeout = Optional.ofNullable(requestTimeout)
                .filter(timeout -> !timeout.isZero() && !timeout.isNegative())
                .orElseThrow(() -> new IllegalArgumentException("requestTimeout must be positive"));
        if (maxDepth < 0) {
            throw new IllegalArgumentException("maxDepth must not be negative");
        }
        if (maxRedirects < 0) {
            throw new IllegalArgumentException("maxRedirects must not be negative");
        }
        if (maxResponseBytes <= 0 || maxResponseBytes == Integer.MAX_VALUE) {
            throw new IllegalArgumentException("maxResponseBytes must be between 1 and Integer.MAX_VALUE - 1");
        }
        userAgent = Optional.ofNullable(userAgent)
                .filter(value -> !value.isBlank())
                .orElseThrow(() -> new IllegalArgumentException("userAgent must not be blank"));
    }

    public static URI parseSeed(String value) {
        String raw = Optional.ofNullable(value)
                .map(String::strip)
                .filter(url -> !url.isEmpty())
                .orElseThrow(() -> new IllegalArgumentException("URL must not be blank"));
        String withScheme = raw.contains("://") ? raw : "https://" + raw;
        return UrlNormalizer.normalize(withScheme)
                .orElseThrow(() -> new IllegalArgumentException("Invalid URL: " + value));
    }
}

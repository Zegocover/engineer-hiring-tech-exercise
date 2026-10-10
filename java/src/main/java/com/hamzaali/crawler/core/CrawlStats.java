package com.hamzaali.crawler.core;

import java.time.Duration;
import java.util.Optional;

public record CrawlStats(int pagesFetched, int pagesSkipped, int pagesFailed, Duration elapsed) {

    public CrawlStats {
        if (pagesFetched < 0 || pagesSkipped < 0 || pagesFailed < 0) {
            throw new IllegalArgumentException("page counts must not be negative");
        }
        elapsed = Optional.ofNullable(elapsed)
                .filter(duration -> !duration.isNegative())
                .orElseThrow(() -> new IllegalArgumentException("elapsed must not be negative"));
    }
}

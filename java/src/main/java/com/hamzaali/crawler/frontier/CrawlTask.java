package com.hamzaali.crawler.frontier;

import java.net.URI;
import java.util.Optional;

public record CrawlTask(URI uri, int depth) {

    public CrawlTask {
        uri = Optional.ofNullable(uri).orElseThrow(() -> new IllegalArgumentException("uri must not be null"));
        if (depth < 0) {
            throw new IllegalArgumentException("depth must not be negative");
        }
    }
}

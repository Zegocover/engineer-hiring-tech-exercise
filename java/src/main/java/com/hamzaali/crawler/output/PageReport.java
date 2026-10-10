package com.hamzaali.crawler.output;

import java.net.URI;
import java.util.Optional;
import java.util.Set;

public record PageReport(URI page, Set<URI> links) {

    public PageReport {
        page = Optional.ofNullable(page).orElseThrow(() -> new IllegalArgumentException("page must not be null"));
        links = Set.copyOf(Optional.ofNullable(links).orElseGet(Set::of));
    }
}

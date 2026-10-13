package com.hamzaali.crawler.url;

import java.net.URI;
import java.util.List;

public final class CompositeScope implements CrawlScope {

    private final List<CrawlScope> parts;

    public CompositeScope(List<CrawlScope> parts) {
        this.parts = List.copyOf(parts);
        if (this.parts.isEmpty()) {
            throw new IllegalArgumentException("parts must not be empty");
        }
    }

    public static CrawlScope of(CrawlScope... scopes) {
        return new CompositeScope(List.of(scopes));
    }

    @Override
    public boolean allows(URI uri) {
        return parts.stream().allMatch(scope -> scope.allows(uri));
    }
}

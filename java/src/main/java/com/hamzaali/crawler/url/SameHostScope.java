package com.hamzaali.crawler.url;

import java.net.URI;
import java.util.Optional;

public final class SameHostScope implements CrawlScope {

    private final String allowedHost;

    public SameHostScope(URI seed) {
        allowedHost = normalizedHost(seed)
                .orElseThrow(() ->
                        new IllegalArgumentException("Seed URL must be an absolute HTTP or HTTPS URL with a host"));
    }

    @Override
    public boolean allows(URI uri) {
        return normalizedHost(uri).map(allowedHost::equals).orElse(false);
    }

    private static Optional<String> normalizedHost(URI uri) {
        return Optional.ofNullable(uri)
                .map(URI::toString)
                .flatMap(UrlNormalizer::normalize)
                .map(URI::getHost);
    }
}

package com.hamzaali.crawler.parse;

import java.net.URI;
import java.util.Set;

@FunctionalInterface
public interface LinkExtractor {

    Set<URI> extractLinks(URI page, String html);
}

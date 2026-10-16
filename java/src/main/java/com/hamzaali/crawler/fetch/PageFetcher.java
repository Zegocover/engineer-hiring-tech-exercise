package com.hamzaali.crawler.fetch;

import java.net.URI;

@FunctionalInterface
public interface PageFetcher {

    FetchResult fetch(URI uri) throws InterruptedException;
}

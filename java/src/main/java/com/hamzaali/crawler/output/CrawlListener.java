package com.hamzaali.crawler.output;

import java.net.URI;

@FunctionalInterface
public interface CrawlListener {

    void onPage(PageReport report);

    default void onSkipped(URI uri, String reason) {}

    default void onFailed(URI uri, String reason, String detail) {}
}

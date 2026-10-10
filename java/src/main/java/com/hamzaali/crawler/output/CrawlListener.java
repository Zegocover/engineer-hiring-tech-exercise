package com.hamzaali.crawler.output;

@FunctionalInterface
public interface CrawlListener {

    void onPage(PageReport report);
}

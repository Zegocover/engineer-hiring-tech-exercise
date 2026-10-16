package com.hamzaali.crawler.url;

import java.net.URI;

@FunctionalInterface
public interface CrawlScope {

    boolean allows(URI uri);
}

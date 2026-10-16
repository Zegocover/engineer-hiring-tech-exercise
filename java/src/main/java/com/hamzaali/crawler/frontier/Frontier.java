package com.hamzaali.crawler.frontier;

import java.net.URI;
import java.time.Duration;
import java.util.Optional;

public interface Frontier {

    boolean offer(URI uri, int depth);

    Optional<CrawlTask> poll(Duration timeout) throws InterruptedException;
}

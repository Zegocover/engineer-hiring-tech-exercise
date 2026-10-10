package com.hamzaali.crawler.frontier;

import java.net.URI;
import java.time.Duration;
import java.util.Optional;
import java.util.Set;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.TimeUnit;

public final class InMemoryFrontier implements Frontier {

    private final Set<URI> seen = ConcurrentHashMap.newKeySet();
    private final BlockingQueue<CrawlTask> queue = new LinkedBlockingQueue<>();
    private final int maxDepth;

    public InMemoryFrontier(int maxDepth) {
        if (maxDepth < 0) {
            throw new IllegalArgumentException("maxDepth must not be negative");
        }
        this.maxDepth = maxDepth;
    }

    @Override
    public boolean offer(URI uri, int depth) {
        return Optional.ofNullable(uri)
                .filter(page -> depth >= 0 && depth <= maxDepth)
                .map(page -> seen.add(page) && queue.offer(new CrawlTask(page, depth)))
                .orElse(false);
    }

    @Override
    public Optional<CrawlTask> poll(Duration timeout) throws InterruptedException {
        Duration wait = Optional.ofNullable(timeout).orElse(Duration.ZERO);
        return Optional.ofNullable(queue.poll(Math.max(wait.toMillis(), 0), TimeUnit.MILLISECONDS));
    }
}

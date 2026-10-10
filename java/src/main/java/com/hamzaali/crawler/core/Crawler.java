package com.hamzaali.crawler.core;

import com.hamzaali.crawler.fetch.FetchResult;
import com.hamzaali.crawler.fetch.FetchResult.Failed;
import com.hamzaali.crawler.fetch.FetchResult.Fetched;
import com.hamzaali.crawler.fetch.FetchResult.Skipped;
import com.hamzaali.crawler.fetch.PageFetcher;
import com.hamzaali.crawler.frontier.CrawlTask;
import com.hamzaali.crawler.frontier.Frontier;
import com.hamzaali.crawler.output.CrawlListener;
import com.hamzaali.crawler.output.PageReport;
import com.hamzaali.crawler.parse.LinkExtractor;
import com.hamzaali.crawler.url.CrawlScope;
import com.hamzaali.crawler.url.UrlNormalizer;
import java.net.URI;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.atomic.AtomicInteger;

public final class Crawler {

    /** How long a worker waits for the next URL before checking whether the crawl is finished. */
    private static final Duration WAIT_FOR_NEXT_TASK = Duration.ofMillis(50);

    private final Frontier frontier;
    private final PageFetcher fetcher;
    private final LinkExtractor linkExtractor;
    private final CrawlScope scope;
    private final CrawlListener listener;
    private final int concurrency;
    private final Clock clock;

    /** Tasks still on the queue plus tasks a worker is currently fetching. */
    private final AtomicInteger unfinishedTasks = new AtomicInteger();

    private final AtomicInteger pagesFetched = new AtomicInteger();
    private final AtomicInteger pagesSkipped = new AtomicInteger();
    private final AtomicInteger pagesFailed = new AtomicInteger();

    public Crawler(
            Frontier frontier,
            PageFetcher fetcher,
            LinkExtractor linkExtractor,
            CrawlScope scope,
            CrawlListener listener,
            int concurrency,
            Clock clock) {
        this.frontier = required(frontier, "frontier");
        this.fetcher = required(fetcher, "fetcher");
        this.linkExtractor = required(linkExtractor, "linkExtractor");
        this.scope = required(scope, "scope");
        this.listener = required(listener, "listener");
        this.clock = required(clock, "clock");
        if (concurrency < 1) {
            throw new IllegalArgumentException("concurrency must be at least 1");
        }
        this.concurrency = concurrency;
    }

    public CrawlStats crawl(URI seed) throws InterruptedException {
        resetCounts();
        accept(canonicalSeed(seed), 0);
        if (unfinishedTasks.get() == 0) {
            throw new IllegalArgumentException("seed could not be queued");
        }

        Instant startedAt = clock.instant();
        runWorkersUntilFinished();
        return new CrawlStats(
                pagesFetched.get(),
                pagesSkipped.get(),
                pagesFailed.get(),
                Duration.between(startedAt, clock.instant()));
    }

    private void runWorkersUntilFinished() throws InterruptedException {
        try (ExecutorService workers = Executors.newVirtualThreadPerTaskExecutor()) {
            for (Future<?> worker : startWorkers(workers)) {
                waitUntilDone(worker);
            }
        }
    }

    private List<Future<?>> startWorkers(ExecutorService workers) {
        List<Future<?>> started = new ArrayList<>();
        for (int index = 0; index < concurrency; index++) {
            started.add(workers.submit(this::workUntilIdle));
        }
        return started;
    }

    private void workUntilIdle() {
        while (hasUnfinishedWork()) {
            nextTask().ifPresent(this::crawlOnePage);
        }
    }

    private Optional<CrawlTask> nextTask() {
        try {
            return frontier.poll(WAIT_FOR_NEXT_TASK);
        } catch (InterruptedException interrupted) {
            Thread.currentThread().interrupt();
            return Optional.empty();
        }
    }

    private void crawlOnePage(CrawlTask task) {
        try {
            recordResult(fetcher.fetch(task.uri()), task.depth());
        } catch (InterruptedException interrupted) {
            Thread.currentThread().interrupt();
        } finally {
            // Children are accepted above, so they are already counted before this parent is marked done.
            unfinishedTasks.decrementAndGet();
        }
    }

    private void recordResult(FetchResult result, int depth) {
        switch (result) {
            case Fetched fetched -> crawlDiscoveredLinks(fetched, depth);
            case Skipped ignored -> pagesSkipped.incrementAndGet();
            case Failed ignored -> pagesFailed.incrementAndGet();
        }
    }

    private void crawlDiscoveredLinks(Fetched fetched, int depth) {
        pagesFetched.incrementAndGet();
        Set<URI> links = linkExtractor.extractLinks(fetched.finalUri(), fetched.html());
        listener.onPage(new PageReport(fetched.finalUri(), links));
        links.stream().filter(scope::allows).forEach(link -> accept(link, depth + 1));
    }

    private void accept(URI uri, int depth) {
        if (frontier.offer(uri, depth)) {
            unfinishedTasks.incrementAndGet();
        }
    }

    private boolean hasUnfinishedWork() {
        return unfinishedTasks.get() > 0;
    }

    private void resetCounts() {
        unfinishedTasks.set(0);
        pagesFetched.set(0);
        pagesSkipped.set(0);
        pagesFailed.set(0);
    }

    private static URI canonicalSeed(URI seed) {
        return UrlNormalizer.normalize(Optional.ofNullable(seed)
                        .map(URI::toString)
                        .orElseThrow(() -> new IllegalArgumentException("seed must not be null")))
                .orElseThrow(() -> new IllegalArgumentException("seed must be an absolute HTTP or HTTPS URL"));
    }

    private static void waitUntilDone(Future<?> worker) throws InterruptedException {
        try {
            worker.get();
        } catch (java.util.concurrent.ExecutionException failed) {
            throw new IllegalStateException("Crawl worker failed", failed.getCause());
        }
    }

    private static <T> T required(T value, String name) {
        return Optional.ofNullable(value).orElseThrow(() -> new IllegalArgumentException(name + " must not be null"));
    }
}

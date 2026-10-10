package com.hamzaali.crawler.cli;

import com.hamzaali.crawler.core.CrawlStats;
import com.hamzaali.crawler.core.Crawler;
import com.hamzaali.crawler.fetch.HttpFetcherConfig;
import com.hamzaali.crawler.fetch.HttpPageFetcher;
import com.hamzaali.crawler.frontier.InMemoryFrontier;
import com.hamzaali.crawler.output.ConsoleCrawlListener;
import com.hamzaali.crawler.parse.JsoupLinkExtractor;
import com.hamzaali.crawler.url.CrawlScope;
import com.hamzaali.crawler.url.SameHostScope;
import java.io.PrintStream;
import java.net.http.HttpClient;
import java.time.Clock;
import java.util.Optional;

public final class CrawlRunner {

    private final PrintStream resultOut;
    private final PrintStream logOut;
    private final Clock clock;

    public CrawlRunner(PrintStream resultOut, PrintStream logOut, Clock clock) {
        this.resultOut = required(resultOut, "resultOut");
        this.logOut = required(logOut, "logOut");
        this.clock = required(clock, "clock");
    }

    public CrawlStats run(CrawlSettings settings) throws InterruptedException {
        CrawlScope scope = new SameHostScope(settings.seed());
        HttpClient client = HttpClient.newBuilder()
                .connectTimeout(settings.requestTimeout())
                .followRedirects(HttpClient.Redirect.NEVER)
                .build();
        Crawler crawler = new Crawler(
                new InMemoryFrontier(settings.maxDepth()),
                new HttpPageFetcher(
                        client,
                        scope,
                        new HttpFetcherConfig(
                                settings.requestTimeout(),
                                settings.maxRedirects(),
                                settings.maxResponseBytes(),
                                settings.userAgent())),
                new JsoupLinkExtractor(),
                scope,
                new ConsoleCrawlListener(resultOut),
                settings.concurrency(),
                clock);
        CrawlStats stats = crawler.crawl(settings.seed());
        printSummary(settings, stats);
        return stats;
    }

    private void printSummary(CrawlSettings settings, CrawlStats stats) {
        logOut.println("Crawl complete for " + settings.seed());
        logOut.println("Pages fetched: " + stats.pagesFetched());
        logOut.println("Pages skipped: " + stats.pagesSkipped());
        logOut.println("Pages failed: " + stats.pagesFailed());
        logOut.println("Elapsed: " + "%.2fs".formatted(stats.elapsed().toMillis() / 1000.0));
    }

    private static <T> T required(T value, String name) {
        return Optional.ofNullable(value).orElseThrow(() -> new IllegalArgumentException(name + " must not be null"));
    }
}

package com.hamzaali.crawler.cli;

import com.hamzaali.crawler.core.CrawlStats;
import com.hamzaali.crawler.core.Crawler;
import com.hamzaali.crawler.fetch.HttpFetcherConfig;
import com.hamzaali.crawler.fetch.HttpPageFetcher;
import com.hamzaali.crawler.fetch.PageFetcher;
import com.hamzaali.crawler.fetch.RetryingPageFetcher;
import com.hamzaali.crawler.frontier.InMemoryFrontier;
import com.hamzaali.crawler.output.ConsoleCrawlListener;
import com.hamzaali.crawler.parse.JsoupLinkExtractor;
import com.hamzaali.crawler.url.CompositeScope;
import com.hamzaali.crawler.url.CrawlScope;
import com.hamzaali.crawler.url.RobotsTxtScope;
import com.hamzaali.crawler.url.SameHostScope;
import java.io.IOException;
import java.io.PrintStream;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Clock;
import java.time.Duration;
import java.util.Optional;

public final class CrawlRunner {

    private static final int FETCH_ATTEMPTS = 3;
    private static final Duration RETRY_BACKOFF = Duration.ofMillis(200);

    private final PrintStream resultOut;
    private final PrintStream logOut;
    private final Clock clock;

    public CrawlRunner(PrintStream resultOut, PrintStream logOut, Clock clock) {
        this.resultOut = required(resultOut, "resultOut");
        this.logOut = required(logOut, "logOut");
        this.clock = required(clock, "clock");
    }

    public CrawlStats run(CrawlSettings settings) throws InterruptedException {
        HttpClient client = HttpClient.newBuilder()
                .connectTimeout(settings.requestTimeout())
                .followRedirects(HttpClient.Redirect.NEVER)
                .build();
        CrawlScope scope = crawlScope(settings, client);
        Crawler crawler = new Crawler(
                new InMemoryFrontier(settings.maxDepth()),
                pageFetcher(settings, client, scope),
                new JsoupLinkExtractor(),
                scope,
                new ConsoleCrawlListener(resultOut, logOut),
                settings.concurrency(),
                settings.maxPages(),
                clock);
        CrawlStats stats = crawler.crawl(settings.seed());
        printSummary(settings, stats);
        return stats;
    }

    private CrawlScope crawlScope(CrawlSettings settings, HttpClient client) throws InterruptedException {
        SameHostScope hostScope = new SameHostScope(settings.seed());
        if (!settings.respectRobots()) {
            return hostScope;
        }
        return CompositeScope.of(hostScope, robotsScope(settings, client));
    }

    private RobotsTxtScope robotsScope(CrawlSettings settings, HttpClient client) throws InterruptedException {
        try {
            HttpResponse<String> response = client.send(
                    HttpRequest.newBuilder(settings.seed().resolve("/robots.txt"))
                            .timeout(settings.requestTimeout())
                            .header("User-Agent", settings.userAgent())
                            .GET()
                            .build(),
                    HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() != 200) {
                return RobotsTxtScope.allowAll();
            }
            return RobotsTxtScope.parse(response.body(), settings.userAgent());
        } catch (IOException ignored) {
            return RobotsTxtScope.allowAll();
        }
    }

    private static PageFetcher pageFetcher(CrawlSettings settings, HttpClient client, CrawlScope scope) {
        return new RetryingPageFetcher(
                new HttpPageFetcher(
                        client,
                        scope,
                        new HttpFetcherConfig(
                                settings.requestTimeout(),
                                settings.maxRedirects(),
                                settings.maxResponseBytes(),
                                settings.userAgent())),
                FETCH_ATTEMPTS,
                RETRY_BACKOFF);
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

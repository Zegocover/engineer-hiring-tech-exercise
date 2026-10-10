package com.hamzaali.crawler.core;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatIllegalArgumentException;

import com.hamzaali.crawler.fetch.FetchResult.Failed;
import com.hamzaali.crawler.fetch.FetchResult.FailureReason;
import com.hamzaali.crawler.fetch.FetchResult.Fetched;
import com.hamzaali.crawler.fetch.PageFetcher;
import com.hamzaali.crawler.frontier.InMemoryFrontier;
import com.hamzaali.crawler.output.CrawlListener;
import com.hamzaali.crawler.output.PageReport;
import com.hamzaali.crawler.parse.JsoupLinkExtractor;
import com.hamzaali.crawler.url.SameHostScope;
import java.net.URI;
import java.time.Clock;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.stream.Collectors;
import org.junit.jupiter.api.Test;

class CrawlerTest {

    private static final URI HOME = URI.create("https://example.com/");
    private static final URI ABOUT = URI.create("https://example.com/about");
    private static final URI CONTACT = URI.create("https://example.com/contact");
    private static final URI EXTERNAL = URI.create("https://other.example/news");
    private static final URI SUBDOMAIN = URI.create("https://sub.example.com/help");

    @Test
    void shouldCrawlLinkedPagesOnTheSameHost() throws InterruptedException {
        PageFetcher fetcher = pages(Map.of(
                HOME, html(ABOUT, CONTACT, EXTERNAL, SUBDOMAIN),
                ABOUT, html(HOME),
                CONTACT, html()));
        RecordingListener listener = new RecordingListener();

        CrawlStats stats = crawler(fetcher, listener, 2, 5).crawl(HOME);

        assertThat(listener.pages()).containsExactlyInAnyOrder(HOME, ABOUT, CONTACT);
        assertThat(listener.linksOn(HOME)).contains(ABOUT, CONTACT, EXTERNAL, SUBDOMAIN);
        assertThat(stats.pagesFetched()).isEqualTo(3);
        assertThat(stats.pagesFailed()).isZero();
    }

    @Test
    void shouldNotFetchExternalOrSubdomainLinks() throws InterruptedException {
        AtomicInteger externalFetches = new AtomicInteger();
        PageFetcher fetcher = uri -> {
            if (uri.equals(EXTERNAL) || uri.equals(SUBDOMAIN)) {
                externalFetches.incrementAndGet();
            }
            return pages(Map.of(HOME, html(EXTERNAL, SUBDOMAIN), ABOUT, html())).fetch(uri);
        };

        crawler(fetcher, new RecordingListener(), 2, 5).crawl(HOME);

        assertThat(externalFetches).hasValue(0);
    }

    @Test
    void shouldVisitEachPageOnlyOnceWhenLinksFormACycle() throws InterruptedException {
        AtomicInteger homeFetches = new AtomicInteger();
        PageFetcher fetcher = uri -> {
            if (uri.equals(HOME)) {
                homeFetches.incrementAndGet();
            }
            return pages(Map.of(HOME, html(ABOUT), ABOUT, html(HOME))).fetch(uri);
        };

        crawler(fetcher, new RecordingListener(), 2, 5).crawl(HOME);

        assertThat(homeFetches).hasValue(1);
    }

    @Test
    void shouldContinueWhenAPageFetchFails() throws InterruptedException {
        PageFetcher fetcher = uri -> uri.equals(ABOUT)
                ? new Failed(ABOUT, ABOUT, FailureReason.CONNECTION, "refused")
                : pages(Map.of(HOME, html(ABOUT, CONTACT), CONTACT, html())).fetch(uri);
        RecordingListener listener = new RecordingListener();

        CrawlStats stats = crawler(fetcher, listener, 2, 5).crawl(HOME);

        assertThat(listener.pages()).containsExactlyInAnyOrder(HOME, CONTACT);
        assertThat(stats.pagesFetched()).isEqualTo(2);
        assertThat(stats.pagesFailed()).isEqualTo(1);
    }

    @Test
    void shouldFollowAChainOfInternalLinks() throws InterruptedException {
        URI level1 = URI.create("https://example.com/level1");
        URI level2 = URI.create("https://example.com/level2");
        PageFetcher fetcher = pages(Map.of(HOME, html(level1), level1, html(level2), level2, html()));
        RecordingListener listener = new RecordingListener();

        crawler(fetcher, listener, 2, 5).crawl(HOME);

        assertThat(listener.pages()).containsExactlyInAnyOrder(HOME, level1, level2);
    }

    @Test
    void shouldRespectMaximumDepth() throws InterruptedException {
        URI level1 = URI.create("https://example.com/level1");
        URI level2 = URI.create("https://example.com/level2");
        PageFetcher fetcher = pages(Map.of(HOME, html(level1), level1, html(level2), level2, html()));
        RecordingListener listener = new RecordingListener();

        crawler(fetcher, listener, 2, 1).crawl(HOME);

        assertThat(listener.pages()).containsExactlyInAnyOrder(HOME, level1);
    }

    @Test
    void shouldNotExceedConfiguredConcurrency() throws InterruptedException {
        URI team = URI.create("https://example.com/team");
        Set<URI> childPages = Set.of(ABOUT, CONTACT, team);
        CountDownLatch childFetchesStarted = new CountDownLatch(3);
        CountDownLatch releaseFetches = new CountDownLatch(1);
        AtomicInteger inFlight = new AtomicInteger();
        AtomicInteger maxInFlight = new AtomicInteger();
        PageFetcher fetcher = uri -> {
            if (childPages.contains(uri)) {
                int current = inFlight.incrementAndGet();
                maxInFlight.updateAndGet(highest -> Math.max(highest, current));
                childFetchesStarted.countDown();
                await(releaseFetches);
                inFlight.decrementAndGet();
            }
            return uri.equals(HOME) ? fetched(HOME, html(ABOUT, CONTACT, team)) : fetched(uri, html());
        };

        Thread crawl = Thread.ofVirtual().start(() -> {
            try {
                crawler(fetcher, new RecordingListener(), 3, 5).crawl(HOME);
            } catch (InterruptedException interrupted) {
                Thread.currentThread().interrupt();
            }
        });
        childFetchesStarted.await();
        releaseFetches.countDown();
        crawl.join();

        assertThat(maxInFlight).hasValue(3);
    }

    @Test
    void shouldRejectConcurrencyBelowOne() {
        assertThatIllegalArgumentException().isThrownBy(() -> crawler(pages(Map.of()), new RecordingListener(), 0, 5));
    }

    private static Crawler crawler(PageFetcher fetcher, CrawlListener listener, int concurrency, int maxDepth) {
        return new Crawler(
                new InMemoryFrontier(maxDepth),
                fetcher,
                new JsoupLinkExtractor(),
                new SameHostScope(HOME),
                listener,
                concurrency,
                Clock.systemUTC());
    }

    private static PageFetcher pages(Map<URI, String> htmlByPage) {
        return uri -> Optional.ofNullable(htmlByPage.get(uri))
                .map(html -> fetched(uri, html))
                .orElseGet(() -> fetched(uri, html()));
    }

    private static Fetched fetched(URI uri, String html) {
        return new Fetched(uri, uri, 200, html);
    }

    private static String html(URI... links) {
        return "<html><body>"
                + List.of(links).stream()
                        .map(link -> "<a href=\"" + link + "\">link</a>")
                        .collect(Collectors.joining())
                + "</body></html>";
    }

    private static void await(CountDownLatch latch) {
        try {
            latch.await();
        } catch (InterruptedException interrupted) {
            Thread.currentThread().interrupt();
        }
    }

    private static final class RecordingListener implements CrawlListener {
        private final ConcurrentLinkedQueue<PageReport> reports = new ConcurrentLinkedQueue<>();

        @Override
        public void onPage(PageReport report) {
            reports.add(report);
        }

        private Set<URI> pages() {
            return reports.stream().map(PageReport::page).collect(Collectors.toSet());
        }

        private Set<URI> linksOn(URI page) {
            return reports.stream()
                    .filter(report -> report.page().equals(page))
                    .findFirst()
                    .map(PageReport::links)
                    .orElseGet(Set::of);
        }
    }
}

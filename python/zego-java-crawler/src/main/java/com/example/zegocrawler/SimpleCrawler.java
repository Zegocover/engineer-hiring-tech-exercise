package com.example.zegocrawler;

import java.net.URI;
import java.net.URISyntaxException;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.Arrays;
import java.util.Set;
import java.util.TreeSet;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class SimpleCrawler {

    private static final int DEFAULT_CONCURRENCY = 10;
    private static final int DEFAULT_MAX_PAGES = 100;
    private static final Duration DEFAULT_TIMEOUT = Duration.ofSeconds(10);
    private static final String DEFAULT_UA = "PureJavaCrawler/1.0 (+https://example.local)";
    private static final int MAX_DOWNLOAD_BYTES = 2 * 1024 * 1024;
    private static final Pattern HREF_PATTERN =
        Pattern.compile("(?i)<a[^>]+href=[\"']?([^\"' >]+)", Pattern.CASE_INSENSITIVE);

    private final HttpClient client;
    private final BlockingQueue<String> queue = new LinkedBlockingQueue<>();
    private final Set<String> seen = ConcurrentHashMap.newKeySet();
    private final AtomicInteger pagesCrawled = new AtomicInteger(0);

    private final String baseHost;
    private final int concurrency;
    private final int maxPages;
    private final Duration timeout;
    private final String userAgent;

    public SimpleCrawler(String baseUrl, int concurrency, int maxPages, Duration timeout,
                         String userAgent) {
        this.concurrency = concurrency;
        this.maxPages = maxPages;
        this.timeout = timeout;
        this.userAgent = userAgent;

        URI start;
        try {
            start = new URI(baseUrl);
        } catch (URISyntaxException e) {
            throw new IllegalArgumentException("Invalid base URL: " + baseUrl);
        }
        if (!isHttpish(start)) {
            throw new IllegalArgumentException("Base URL must be http or https: " + baseUrl);
        }
        this.baseHost = start.getHost();
        if (this.baseHost == null || this.baseHost.isEmpty()) {
            throw new IllegalArgumentException("Base URL must include a host: " + baseUrl);
        }

        this.client = HttpClient.newBuilder()
            .followRedirects(HttpClient.Redirect.NORMAL)
            .connectTimeout(timeout)
            .build();

        queue.offer(baseUrl);
        seen.add(baseUrl);
    }

    static boolean isHttpish(URI uri) {
        String s = uri.getScheme();
        return "http".equalsIgnoreCase(s) || "https".equalsIgnoreCase(s);
    }

    static String normalize(String base, String href) {
        if (href == null || href.isEmpty()) {
            return null;
        }
        href = href.trim();
        String lower = href.toLowerCase();
        if (lower.startsWith("#") ||
            lower.startsWith("javascript:") ||
            lower.startsWith("mailto:") ||
            lower.startsWith("tel:") ||
            lower.startsWith("sms:") ||
            lower.startsWith("data:")) {
            return null;
        }
        try {
            URI abs = new URI(base).resolve(href);
            if (!isHttpish(abs)) {
                return null;
            }
            String url = abs.toString();
            int idx = url.indexOf('#');
            if (idx > 0) {
                url = url.substring(0, idx);
            }
            return url;
        } catch (URISyntaxException e) {
            return null;
        }
    }

    boolean sameExactHost(String url) {
        try {
            URI u = new URI(url);
            String host = u.getHost();
            return host != null && host.equalsIgnoreCase(baseHost);
        } catch (URISyntaxException e) {
            return false;
        }
    }

    static boolean looksLikeHtml(HttpResponse<byte[]> resp) {
        return resp.headers().firstValue("content-type")
            .map(ct -> ct.toLowerCase().contains("text/html")).orElse(false);
    }

    void fetchAndParse(String url) {
        if (pagesCrawled.get() >= maxPages) {
            return;
        }
        try {
            HttpRequest req = HttpRequest.newBuilder(URI.create(url))
                .timeout(timeout)
                .header("User-Agent", userAgent)
                .header("Accept", "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8")
                .GET()
                .build();
            HttpResponse<byte[]> resp = client.send(req, HttpResponse.BodyHandlers.ofByteArray());
            String finalUrl = resp.uri().toString();
            if (!looksLikeHtml(resp)) {
                System.out.println(finalUrl + "\n");
                pagesCrawled.incrementAndGet();
                return;
            }

            byte[] data = resp.body();
            if (data.length > MAX_DOWNLOAD_BYTES) {
                data = Arrays.copyOf(data, MAX_DOWNLOAD_BYTES);
            }
            String html = new String(data);
            Set<String> links = extractLinks(finalUrl, html);

            System.out.println(finalUrl);
            for (String link : links) {
                System.out.println(link);
            }
            System.out.println();

            for (String link : links) {
                if (sameExactHost(link) && seen.add(link)) {
                    queue.offer(link);
                }
            }
            pagesCrawled.incrementAndGet();
        } catch (Exception ignored) {
            // In a production system we would log/metric this; for the exercise we keep output clean.
        }
    }

    static Set<String> extractLinks(String base, String html) {
        Set<String> links = new TreeSet<>();
        Matcher m = HREF_PATTERN.matcher(html);
        while (m.find()) {
            String href = m.group(1);
            String abs = normalize(base, href);
            if (abs != null) {
                links.add(abs);
            }
        }
        return links;
    }

    public void run() throws InterruptedException {
        ExecutorService pool = Executors.newFixedThreadPool(concurrency);
        for (int i = 0; i < concurrency; i++) {
            pool.submit(() -> {
                try {
                    workerLoop();
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
            });
        }
        pool.shutdown();
        pool.awaitTermination(1, TimeUnit.HOURS);
    }

    private void workerLoop() throws InterruptedException {
        while (true) {
            if (pagesCrawled.get() >= maxPages) {
                return;
            }
            String next = queue.poll(200, TimeUnit.MILLISECONDS);
            if (next == null) {
                // If queue appears drained and we've hit the page limit, exit.
                if (queue.isEmpty() && pagesCrawled.get() >= maxPages) {
                    return;
                }
                // Otherwise, just wait for more work.
                continue;
            }
            fetchAndParse(next);
        }
    }

    public static void main(String[] args) throws Exception {
        if (args.length == 0) {
            System.err.println(
                "Usage: java SimpleCrawler <base_url> [--concurrency N] [--max-pages N]");
            System.exit(2);
        }

        String baseUrl = null;
        int concurrency = DEFAULT_CONCURRENCY;
        int maxPages = DEFAULT_MAX_PAGES;

        for (int i = 0; i < args.length; i++) {
            String a = args[i];
            switch (a) {
                case "--concurrency":
                    concurrency = Integer.parseInt(args[++i]);
                    break;
                case "--max-pages":
                    maxPages = Integer.parseInt(args[++i]);
                    break;
                default:
                    if (!a.startsWith("--")) {
                        baseUrl = a;
                    }
            }
        }

        if (baseUrl == null) {
            System.err.println("Error: base_url required");
            System.exit(1);
        }

        System.err.printf("Starting crawl: base=%s, concurrency=%d, max-pages=%d%n",
            baseUrl, concurrency, maxPages);

        SimpleCrawler crawler = new SimpleCrawler(baseUrl, concurrency, maxPages, DEFAULT_TIMEOUT,
            DEFAULT_UA);
        crawler.run();
    }
}

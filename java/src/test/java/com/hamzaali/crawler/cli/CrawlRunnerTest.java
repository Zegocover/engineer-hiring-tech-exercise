package com.hamzaali.crawler.cli;

import static org.assertj.core.api.Assertions.assertThat;

import com.hamzaali.crawler.core.CrawlStats;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.PrintStream;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.time.Clock;
import java.time.Duration;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class CrawlRunnerTest {

    private HttpServer server;
    private ExecutorService serverExecutor;
    private URI baseUri;

    @BeforeEach
    void startServer() throws IOException {
        InetAddress loopback = InetAddress.getLoopbackAddress();
        server = HttpServer.create(new InetSocketAddress(loopback, 0), 0);
        serverExecutor = Executors.newVirtualThreadPerTaskExecutor();
        server.setExecutor(serverExecutor);
        server.start();
        baseUri = URI.create("http://" + loopback.getHostAddress() + ":"
                + server.getAddress().getPort() + "/");
    }

    @AfterEach
    void stopServer() {
        server.stop(0);
        serverExecutor.close();
    }

    @Test
    void shouldCrawlLinkedPagesAndPrintThemToStdout() throws InterruptedException {
        serve("/", html(baseUri.resolve("/about")));
        serve("/about", html());
        serve("/robots.txt", "User-agent: *\nDisallow:\n", "text/plain");

        ByteArrayOutputStream stdout = new ByteArrayOutputStream();
        ByteArrayOutputStream stderr = new ByteArrayOutputStream();
        CrawlStats stats = runner(stdout, stderr).run(settings(baseUri, 0, true));

        assertThat(stdout.toString(StandardCharsets.UTF_8))
                .contains(baseUri.toString())
                .contains(baseUri.resolve("/about").toString());
        assertThat(stderr.toString(StandardCharsets.UTF_8)).contains("Pages fetched: 2");
        assertThat(stats.pagesFetched()).isEqualTo(2);
    }

    @Test
    void shouldNotFetchPathsDisallowedByRobotsTxt() throws InterruptedException {
        AtomicInteger secretFetches = new AtomicInteger();
        serve("/", html(baseUri.resolve("/secret"), baseUri.resolve("/about")));
        serve("/about", html());
        server.createContext("/secret", exchange -> {
            secretFetches.incrementAndGet();
            respond(exchange, 200, "text/html", html());
        });
        serve("/robots.txt", "User-agent: *\nDisallow: /secret\n", "text/plain");

        ByteArrayOutputStream stdout = new ByteArrayOutputStream();
        CrawlStats stats = runner(stdout, new ByteArrayOutputStream()).run(settings(baseUri, 0, true));

        assertThat(secretFetches).hasValue(0);
        assertThat(stdout.toString(StandardCharsets.UTF_8).lines())
                .doesNotContain(baseUri.resolve("/secret").toString());
        assertThat(stats.pagesFetched()).isEqualTo(2);
    }

    @Test
    void shouldPrintSkippedPagesToStderrWithoutChangingStdoutFormat() throws InterruptedException {
        serve("/", html(baseUri.resolve("/missing")));
        serve("/robots.txt", "User-agent: *\nDisallow:\n", "text/plain");
        server.createContext("/missing", exchange -> respond(exchange, 404, "text/html", "gone"));

        ByteArrayOutputStream stdout = new ByteArrayOutputStream();
        ByteArrayOutputStream stderr = new ByteArrayOutputStream();
        runner(stdout, stderr).run(settings(baseUri, 0, true));

        assertThat(stdout.toString(StandardCharsets.UTF_8)).startsWith(baseUri.toString());
        assertThat(stderr.toString(StandardCharsets.UTF_8))
                .contains("skipped " + baseUri.resolve("/missing") + " (HTTP_STATUS)");
    }

    @Test
    void shouldHonourThePageCap() throws InterruptedException {
        serve("/", html(baseUri.resolve("/about")));
        serve("/about", html());
        serve("/robots.txt", "User-agent: *\nDisallow:\n", "text/plain");

        CrawlStats stats =
                runner(new ByteArrayOutputStream(), new ByteArrayOutputStream()).run(settings(baseUri, 1, true));

        assertThat(stats.pagesFetched()).isEqualTo(1);
    }

    private static CrawlRunner runner(ByteArrayOutputStream stdout, ByteArrayOutputStream stderr) {
        return new CrawlRunner(
                new PrintStream(stdout, true, StandardCharsets.UTF_8),
                new PrintStream(stderr, true, StandardCharsets.UTF_8),
                Clock.systemUTC());
    }

    private static CrawlSettings settings(URI seed, int maxPages, boolean respectRobots) {
        return new CrawlSettings(
                seed, 2, Duration.ofSeconds(2), 5, maxPages, 3, 20_000, CrawlCommand.DEFAULT_USER_AGENT, respectRobots);
    }

    private void serve(String path, String body) {
        serve(path, body, "text/html");
    }

    private void serve(String path, String body, String contentType) {
        server.createContext(path, exchange -> respond(exchange, 200, contentType, body));
    }

    private static String html(URI... links) {
        StringBuilder markup = new StringBuilder("<html><body>");
        for (URI link : links) {
            markup.append("<a href=\"").append(link).append("\">link</a>");
        }
        return markup.append("</body></html>").toString();
    }

    private static void respond(HttpExchange exchange, int status, String contentType, String body) throws IOException {
        byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
        exchange.getResponseHeaders().add("Content-Type", contentType);
        exchange.sendResponseHeaders(status, bytes.length);
        try (exchange;
                var responseBody = exchange.getResponseBody()) {
            responseBody.write(bytes);
        }
    }
}

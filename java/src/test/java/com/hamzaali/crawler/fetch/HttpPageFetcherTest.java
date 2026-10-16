package com.hamzaali.crawler.fetch;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatIllegalArgumentException;

import com.hamzaali.crawler.fetch.FetchResult.Failed;
import com.hamzaali.crawler.fetch.FetchResult.FailureReason;
import com.hamzaali.crawler.fetch.FetchResult.Fetched;
import com.hamzaali.crawler.fetch.FetchResult.SkipReason;
import com.hamzaali.crawler.fetch.FetchResult.Skipped;
import com.hamzaali.crawler.url.SameHostScope;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.URI;
import java.net.URISyntaxException;
import java.net.http.HttpClient;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class HttpPageFetcherTest {

    private static final String USER_AGENT = "ZegoCrawler/0.1";

    private HttpServer server;
    private ExecutorService serverExecutor;
    private URI baseUri;

    @BeforeEach
    void startServer() throws IOException, URISyntaxException {
        InetAddress loopback = InetAddress.getLoopbackAddress();
        server = HttpServer.create(new InetSocketAddress(loopback, 0), 0);
        serverExecutor = Executors.newVirtualThreadPerTaskExecutor();
        server.setExecutor(serverExecutor);
        server.start();
        baseUri = new URI(
                "http", null, loopback.getHostAddress(), server.getAddress().getPort(), null, null, null);
    }

    @AfterEach
    void stopServer() {
        server.stop(0);
        serverExecutor.close();
    }

    @Test
    void shouldFetchHtmlUsingDeclaredCharset() throws InterruptedException {
        byte[] body = "<html><a href=\"/café\">Café</a></html>".getBytes(StandardCharsets.ISO_8859_1);
        server.createContext("/html", exchange -> respond(exchange, 200, "text/html; charset=ISO-8859-1", body));

        FetchResult result = fetcher(defaultConfig()).fetch(baseUri.resolve("/html"));

        assertThat(result).isInstanceOfSatisfying(Fetched.class, fetched -> {
            assertThat(fetched.statusCode()).isEqualTo(200);
            assertThat(fetched.finalUri()).isEqualTo(baseUri.resolve("/html"));
            assertThat(fetched.html()).contains("Café");
        });
    }

    @Test
    void shouldSendConfiguredUserAgent() throws InterruptedException {
        AtomicReference<String> receivedUserAgent = new AtomicReference<>();
        server.createContext("/headers", exchange -> {
            receivedUserAgent.set(exchange.getRequestHeaders().getFirst("User-Agent"));
            respond(exchange, 200, "text/html", "<html></html>");
        });

        fetcher(defaultConfig()).fetch(baseUri.resolve("/headers"));

        assertThat(receivedUserAgent).hasValue(USER_AGENT);
    }

    @Test
    void shouldSkipNonSuccessfulStatus() throws InterruptedException {
        server.createContext("/missing", exchange -> respond(exchange, 404, "text/html", "not found"));

        FetchResult result = fetcher(defaultConfig()).fetch(baseUri.resolve("/missing"));

        assertThat(result).isInstanceOfSatisfying(Skipped.class, skipped -> {
            assertThat(skipped.reason()).isEqualTo(SkipReason.HTTP_STATUS);
            assertThat(skipped.statusCode()).hasValue(404);
        });
    }

    @Test
    void shouldSkipUnsupportedContentType() throws InterruptedException {
        server.createContext("/document", exchange -> respond(exchange, 200, "application/pdf", "pdf"));

        FetchResult result = fetcher(defaultConfig()).fetch(baseUri.resolve("/document"));

        assertThat(result)
                .isInstanceOfSatisfying(
                        Skipped.class,
                        skipped -> assertThat(skipped.reason()).isEqualTo(SkipReason.UNSUPPORTED_CONTENT_TYPE));
    }

    @Test
    void shouldRejectResponseWhenBodyExceedsLimit() throws InterruptedException {
        server.createContext("/large", exchange -> respond(exchange, 200, "text/html", "0123456789"));
        HttpFetcherConfig config = new HttpFetcherConfig(Duration.ofSeconds(1), 3, 5, USER_AGENT);

        FetchResult result = fetcher(config).fetch(baseUri.resolve("/large"));

        assertThat(result)
                .isInstanceOfSatisfying(
                        Failed.class,
                        failed -> assertThat(failed.reason()).isEqualTo(FailureReason.RESPONSE_TOO_LARGE));
    }

    @Test
    void shouldFollowInScopeRedirect() throws InterruptedException {
        server.createContext("/start", exchange -> redirect(exchange, "/target"));
        server.createContext("/target", exchange -> respond(exchange, 200, "text/html", "<html>target</html>"));

        FetchResult result = fetcher(defaultConfig()).fetch(baseUri.resolve("/start"));

        assertThat(result).isInstanceOfSatisfying(Fetched.class, fetched -> {
            assertThat(fetched.requestedUri()).isEqualTo(baseUri.resolve("/start"));
            assertThat(fetched.finalUri()).isEqualTo(baseUri.resolve("/target"));
        });
    }

    @Test
    void shouldRejectRedirectBeforeRequestingOutOfScopeTarget() throws InterruptedException {
        AtomicInteger targetRequests = new AtomicInteger();
        server.createContext(
                "/start",
                exchange -> redirect(
                        exchange, "http://localhost:" + server.getAddress().getPort() + "/target"));
        server.createContext("/target", exchange -> {
            targetRequests.incrementAndGet();
            respond(exchange, 200, "text/html", "<html></html>");
        });

        FetchResult result = fetcher(defaultConfig()).fetch(baseUri.resolve("/start"));

        assertThat(result)
                .isInstanceOfSatisfying(
                        Skipped.class, skipped -> assertThat(skipped.reason()).isEqualTo(SkipReason.OUT_OF_SCOPE));
        assertThat(targetRequests).hasValue(0);
    }

    @Test
    void shouldStopWhenRedirectLimitIsReached() throws InterruptedException {
        server.createContext("/one", exchange -> redirect(exchange, "/two"));
        server.createContext("/two", exchange -> redirect(exchange, "/three"));
        HttpFetcherConfig config = new HttpFetcherConfig(Duration.ofSeconds(1), 1, 1_000, USER_AGENT);

        FetchResult result = fetcher(config).fetch(baseUri.resolve("/one"));

        assertThat(result)
                .isInstanceOfSatisfying(
                        Skipped.class,
                        skipped -> assertThat(skipped.reason()).isEqualTo(SkipReason.TOO_MANY_REDIRECTS));
    }

    @Test
    void shouldFailWhenRedirectLocationIsInvalid() throws InterruptedException {
        server.createContext("/redirect", exchange -> redirect(exchange, "http://"));

        FetchResult result = fetcher(defaultConfig()).fetch(baseUri.resolve("/redirect"));

        assertThat(result)
                .isInstanceOfSatisfying(
                        Failed.class, failed -> assertThat(failed.reason()).isEqualTo(FailureReason.INVALID_REDIRECT));
    }

    @Test
    void shouldReturnTimeoutWhenServerDoesNotRespondInTime() throws InterruptedException {
        CountDownLatch releaseResponse = new CountDownLatch(1);
        server.createContext("/slow", exchange -> {
            await(releaseResponse);
            respond(exchange, 200, "text/html", "<html></html>");
        });
        HttpFetcherConfig config = new HttpFetcherConfig(Duration.ofMillis(100), 3, 1_000, USER_AGENT);

        FetchResult result;
        try {
            result = fetcher(config).fetch(baseUri.resolve("/slow"));
        } finally {
            releaseResponse.countDown();
        }

        assertThat(result)
                .isInstanceOfSatisfying(
                        Failed.class, failed -> assertThat(failed.reason()).isEqualTo(FailureReason.TIMEOUT));
    }

    @Test
    void shouldRejectHttpClientThatAutomaticallyFollowsRedirects() {
        HttpClient redirectingClient = HttpClient.newBuilder()
                .followRedirects(HttpClient.Redirect.NORMAL)
                .build();

        assertThatIllegalArgumentException()
                .isThrownBy(() -> new HttpPageFetcher(redirectingClient, new SameHostScope(baseUri), defaultConfig()));
    }

    private HttpPageFetcher fetcher(HttpFetcherConfig config) {
        HttpClient client = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(1))
                .followRedirects(HttpClient.Redirect.NEVER)
                .build();
        return new HttpPageFetcher(client, new SameHostScope(baseUri), config);
    }

    private static HttpFetcherConfig defaultConfig() {
        return new HttpFetcherConfig(Duration.ofSeconds(1), 3, 1_000, USER_AGENT);
    }

    private static void redirect(HttpExchange exchange, String location) throws IOException {
        exchange.getResponseHeaders().add("Location", location);
        exchange.sendResponseHeaders(302, -1);
        exchange.close();
    }

    private static void respond(HttpExchange exchange, int status, String contentType, String body) throws IOException {
        respond(exchange, status, contentType, body.getBytes(StandardCharsets.UTF_8));
    }

    private static void respond(HttpExchange exchange, int status, String contentType, byte[] body) throws IOException {
        exchange.getResponseHeaders().add("Content-Type", contentType);
        exchange.sendResponseHeaders(status, body.length);
        try (exchange;
                var responseBody = exchange.getResponseBody()) {
            responseBody.write(body);
        }
    }

    private static void await(CountDownLatch latch) {
        try {
            latch.await(2, TimeUnit.SECONDS);
        } catch (InterruptedException interrupted) {
            Thread.currentThread().interrupt();
        }
    }
}

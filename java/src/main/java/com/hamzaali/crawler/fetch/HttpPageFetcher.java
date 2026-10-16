package com.hamzaali.crawler.fetch;

import com.hamzaali.crawler.fetch.FetchResult.Failed;
import com.hamzaali.crawler.fetch.FetchResult.FailureReason;
import com.hamzaali.crawler.fetch.FetchResult.Fetched;
import com.hamzaali.crawler.fetch.FetchResult.SkipReason;
import com.hamzaali.crawler.fetch.FetchResult.Skipped;
import com.hamzaali.crawler.url.CrawlScope;
import com.hamzaali.crawler.url.UrlNormalizer;
import java.io.IOException;
import java.io.InputStream;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpHeaders;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.net.http.HttpTimeoutException;
import java.nio.charset.Charset;
import java.nio.charset.StandardCharsets;
import java.util.Locale;
import java.util.Objects;
import java.util.Optional;
import java.util.OptionalInt;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class HttpPageFetcher implements PageFetcher {

    private static final Set<Integer> REDIRECT_STATUS_CODES = Set.of(301, 302, 303, 307, 308);
    private static final Set<String> HTML_CONTENT_TYPES = Set.of("text/html", "application/xhtml+xml");
    private static final Pattern CHARSET_PARAMETER =
            Pattern.compile("(?:^|;)\\s*charset\\s*=\\s*\"?([^;\"\\s]+)", Pattern.CASE_INSENSITIVE);

    private final HttpClient httpClient;
    private final CrawlScope crawlScope;
    private final HttpFetcherConfig config;

    public HttpPageFetcher(HttpClient httpClient, CrawlScope crawlScope, HttpFetcherConfig config) {
        this.httpClient = Objects.requireNonNull(httpClient, "httpClient must not be null");
        this.crawlScope = Objects.requireNonNull(crawlScope, "crawlScope must not be null");
        this.config = Objects.requireNonNull(config, "config must not be null");

        if (httpClient.followRedirects() != HttpClient.Redirect.NEVER) {
            throw new IllegalArgumentException("httpClient must not follow redirects automatically");
        }
    }

    @Override
    public FetchResult fetch(URI uri) throws InterruptedException {
        URI requestedUri = normalizedUri(uri)
                .orElseThrow(() -> new IllegalArgumentException("URI must be an absolute HTTP or HTTPS URL"));
        URI currentUri = requestedUri;
        int redirectsFollowed = 0;

        while (true) {
            if (!crawlScope.allows(currentUri)) {
                return skipped(requestedUri, currentUri, SkipReason.OUT_OF_SCOPE);
            }

            HttpResponse<InputStream> response;
            try {
                response = httpClient.send(request(currentUri), HttpResponse.BodyHandlers.ofInputStream());
            } catch (HttpTimeoutException timeout) {
                return failed(requestedUri, currentUri, FailureReason.TIMEOUT, timeout);
            } catch (IOException connectionFailure) {
                return failed(requestedUri, currentUri, FailureReason.CONNECTION, connectionFailure);
            }

            try (InputStream responseBody = response.body()) {
                int statusCode = response.statusCode();
                if (REDIRECT_STATUS_CODES.contains(statusCode)) {
                    if (redirectsFollowed == config.maxRedirects()) {
                        return skipped(requestedUri, currentUri, statusCode, SkipReason.TOO_MANY_REDIRECTS);
                    }
                    Optional<URI> redirectTarget = redirectTarget(currentUri, response.headers());
                    if (redirectTarget.isEmpty()) {
                        return new Failed(
                                requestedUri,
                                currentUri,
                                FailureReason.INVALID_REDIRECT,
                                "Redirect response did not contain a valid Location header");
                    }
                    currentUri = redirectTarget.get();
                    redirectsFollowed++;
                    continue;
                }

                if (statusCode < 200 || statusCode >= 300) {
                    return skipped(requestedUri, currentUri, statusCode, SkipReason.HTTP_STATUS);
                }
                if (!isHtml(response.headers())) {
                    return skipped(requestedUri, currentUri, statusCode, SkipReason.UNSUPPORTED_CONTENT_TYPE);
                }
                if (isDeclaredBodyTooLarge(response.headers())) {
                    return responseTooLarge(requestedUri, currentUri);
                }

                byte[] body = responseBody.readNBytes(config.maxResponseBytes() + 1);
                if (body.length > config.maxResponseBytes()) {
                    return responseTooLarge(requestedUri, currentUri);
                }
                String html = new String(body, responseCharset(response.headers()));
                return new Fetched(requestedUri, currentUri, statusCode, html);
            } catch (IOException connectionFailure) {
                return failed(requestedUri, currentUri, FailureReason.CONNECTION, connectionFailure);
            }
        }
    }

    private HttpRequest request(URI uri) {
        return HttpRequest.newBuilder(uri)
                .timeout(config.requestTimeout())
                .header("User-Agent", config.userAgent())
                .header("Accept", "text/html, application/xhtml+xml")
                .header("Accept-Encoding", "identity")
                .GET()
                .build();
    }

    private static Optional<URI> redirectTarget(URI currentUri, HttpHeaders headers) {
        return headers.firstValue("Location").flatMap(location -> UrlNormalizer.resolve(currentUri, location));
    }

    private static Optional<URI> normalizedUri(URI uri) {
        return Optional.ofNullable(uri).map(URI::toString).flatMap(UrlNormalizer::normalize);
    }

    private static boolean isHtml(HttpHeaders headers) {
        return headers.firstValue("Content-Type")
                .map(contentType -> contentType.split(";", 2)[0].strip().toLowerCase(Locale.ROOT))
                .filter(HTML_CONTENT_TYPES::contains)
                .isPresent();
    }

    private boolean isDeclaredBodyTooLarge(HttpHeaders headers) {
        return headers.firstValue("Content-Length")
                .flatMap(HttpPageFetcher::parseContentLength)
                .filter(contentLength -> contentLength > config.maxResponseBytes())
                .isPresent();
    }

    private static Optional<Long> parseContentLength(String value) {
        try {
            return Optional.of(Long.parseLong(value));
        } catch (NumberFormatException malformedContentLength) {
            return Optional.empty();
        }
    }

    private static Charset responseCharset(HttpHeaders headers) {
        return headers.firstValue("Content-Type")
                .flatMap(HttpPageFetcher::declaredCharset)
                .orElse(StandardCharsets.UTF_8);
    }

    private static Optional<Charset> declaredCharset(String contentType) {
        Matcher matcher = CHARSET_PARAMETER.matcher(contentType);
        if (!matcher.find()) {
            return Optional.empty();
        }
        try {
            return Optional.of(Charset.forName(matcher.group(1)));
        } catch (IllegalArgumentException unsupportedCharset) {
            return Optional.empty();
        }
    }

    private static Skipped skipped(URI requestedUri, URI finalUri, SkipReason reason) {
        return new Skipped(requestedUri, finalUri, OptionalInt.empty(), reason);
    }

    private static Skipped skipped(URI requestedUri, URI finalUri, int statusCode, SkipReason reason) {
        return new Skipped(requestedUri, finalUri, OptionalInt.of(statusCode), reason);
    }

    private static Failed responseTooLarge(URI requestedUri, URI finalUri) {
        return new Failed(
                requestedUri,
                finalUri,
                FailureReason.RESPONSE_TOO_LARGE,
                "Response body exceeded the configured size limit");
    }

    private static Failed failed(URI requestedUri, URI finalUri, FailureReason reason, IOException failure) {
        String detail = Optional.ofNullable(failure.getMessage())
                .filter(message -> !message.isBlank())
                .orElse(failure.getClass().getSimpleName());
        return new Failed(requestedUri, finalUri, reason, detail);
    }
}

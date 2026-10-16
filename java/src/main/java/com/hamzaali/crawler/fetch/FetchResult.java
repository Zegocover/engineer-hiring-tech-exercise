package com.hamzaali.crawler.fetch;

import java.net.URI;
import java.util.OptionalInt;

public sealed interface FetchResult permits FetchResult.Fetched, FetchResult.Skipped, FetchResult.Failed {

    URI requestedUri();

    URI finalUri();

    record Fetched(URI requestedUri, URI finalUri, int statusCode, String html) implements FetchResult {}

    record Skipped(URI requestedUri, URI finalUri, OptionalInt statusCode, SkipReason reason) implements FetchResult {}

    record Failed(URI requestedUri, URI finalUri, FailureReason reason, String detail) implements FetchResult {}

    enum SkipReason {
        HTTP_STATUS,
        UNSUPPORTED_CONTENT_TYPE,
        OUT_OF_SCOPE,
        TOO_MANY_REDIRECTS,
        PAGE_LIMIT
    }

    enum FailureReason {
        CONNECTION,
        TIMEOUT,
        RESPONSE_TOO_LARGE,
        INVALID_REDIRECT
    }
}

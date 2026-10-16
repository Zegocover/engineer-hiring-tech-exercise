package com.hamzaali.crawler.fetch;

import com.hamzaali.crawler.fetch.FetchResult.Failed;
import com.hamzaali.crawler.fetch.FetchResult.FailureReason;
import java.net.URI;
import java.time.Duration;
import java.util.Optional;
import java.util.Set;

public final class RetryingPageFetcher implements PageFetcher {

    private static final Set<FailureReason> TRANSIENT_FAILURES =
            Set.of(FailureReason.CONNECTION, FailureReason.TIMEOUT);

    private final PageFetcher delegate;
    private final int maxAttempts;
    private final Duration initialBackoff;

    public RetryingPageFetcher(PageFetcher delegate, int maxAttempts, Duration initialBackoff) {
        this.delegate = Optional.ofNullable(delegate)
                .orElseThrow(() -> new IllegalArgumentException("delegate must not be null"));
        if (maxAttempts < 1) {
            throw new IllegalArgumentException("maxAttempts must be at least 1");
        }
        this.maxAttempts = maxAttempts;
        this.initialBackoff = Optional.ofNullable(initialBackoff)
                .filter(value -> !value.isNegative())
                .orElseThrow(() -> new IllegalArgumentException("initialBackoff must not be negative"));
    }

    @Override
    public FetchResult fetch(URI uri) throws InterruptedException {
        FetchResult last = delegate.fetch(uri);
        int attempt = 1;
        while (attempt < maxAttempts && isTransient(last)) {
            sleepQuietly(initialBackoff.multipliedBy(1L << (attempt - 1)));
            last = delegate.fetch(uri);
            attempt++;
        }
        return last;
    }

    private static boolean isTransient(FetchResult result) {
        return result instanceof Failed failed && TRANSIENT_FAILURES.contains(failed.reason());
    }

    private static void sleepQuietly(Duration delay) throws InterruptedException {
        if (!delay.isZero()) {
            Thread.sleep(delay.toMillis());
        }
    }
}

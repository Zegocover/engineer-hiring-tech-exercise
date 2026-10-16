package com.hamzaali.crawler.fetch;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatIllegalArgumentException;

import com.hamzaali.crawler.fetch.FetchResult.Failed;
import com.hamzaali.crawler.fetch.FetchResult.FailureReason;
import com.hamzaali.crawler.fetch.FetchResult.Fetched;
import com.hamzaali.crawler.fetch.FetchResult.SkipReason;
import com.hamzaali.crawler.fetch.FetchResult.Skipped;
import java.net.URI;
import java.time.Duration;
import java.util.OptionalInt;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.Test;

class RetryingPageFetcherTest {

    private static final URI HOME = URI.create("https://example.com/");

    @Test
    void shouldRetryTransientConnectionFailuresThenReturnSuccess() throws InterruptedException {
        AtomicInteger attempts = new AtomicInteger();
        PageFetcher flaky = uri -> {
            if (attempts.incrementAndGet() < 3) {
                return new Failed(HOME, HOME, FailureReason.CONNECTION, "refused");
            }
            return new Fetched(HOME, HOME, 200, "<html></html>");
        };

        FetchResult result = new RetryingPageFetcher(flaky, 3, Duration.ZERO).fetch(HOME);

        assertThat(attempts).hasValue(3);
        assertThat(result).isInstanceOf(Fetched.class);
    }

    @Test
    void shouldNotRetrySkipsOrNonTransientFailures() throws InterruptedException {
        AtomicInteger attempts = new AtomicInteger();
        PageFetcher fetcher = uri -> {
            attempts.incrementAndGet();
            return new Skipped(HOME, HOME, OptionalInt.of(404), SkipReason.HTTP_STATUS);
        };

        FetchResult result = new RetryingPageFetcher(fetcher, 3, Duration.ZERO).fetch(HOME);

        assertThat(attempts).hasValue(1);
        assertThat(result).isInstanceOf(Skipped.class);
    }

    @Test
    void shouldGiveUpAfterTheConfiguredAttempts() throws InterruptedException {
        AtomicInteger attempts = new AtomicInteger();
        PageFetcher fetcher = uri -> {
            attempts.incrementAndGet();
            return new Failed(HOME, HOME, FailureReason.TIMEOUT, "slow");
        };

        FetchResult result = new RetryingPageFetcher(fetcher, 2, Duration.ZERO).fetch(HOME);

        assertThat(attempts).hasValue(2);
        assertThat(result)
                .isInstanceOfSatisfying(
                        Failed.class, failed -> assertThat(failed.reason()).isEqualTo(FailureReason.TIMEOUT));
    }

    @Test
    void shouldRejectZeroAttempts() {
        assertThatIllegalArgumentException()
                .isThrownBy(() -> new RetryingPageFetcher(uri -> new Fetched(HOME, HOME, 200, ""), 0, Duration.ZERO));
    }
}

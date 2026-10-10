package com.hamzaali.crawler.frontier;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatIllegalArgumentException;

import java.net.URI;
import java.time.Duration;
import java.util.Optional;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.Test;

class InMemoryFrontierTest {

    private static final URI HOME = URI.create("https://example.com/");
    private static final URI ABOUT = URI.create("https://example.com/about");

    @Test
    void shouldAcceptUrlTheFirstTimeItIsOffered() {
        InMemoryFrontier frontier = new InMemoryFrontier(2);

        assertThat(frontier.offer(HOME, 0)).isTrue();
    }

    @Test
    void shouldRejectUrlWhenItHasAlreadyBeenSeen() {
        InMemoryFrontier frontier = new InMemoryFrontier(2);
        frontier.offer(HOME, 0);

        assertThat(frontier.offer(HOME, 1)).isFalse();
    }

    @Test
    void shouldRejectUrlWhenDepthExceedsLimit() {
        InMemoryFrontier frontier = new InMemoryFrontier(1);

        assertThat(frontier.offer(HOME, 0)).isTrue();
        assertThat(frontier.offer(ABOUT, 1)).isTrue();
        assertThat(frontier.offer(URI.create("https://example.com/too-deep"), 2))
                .isFalse();
    }

    @Test
    void shouldReturnQueuedTasksInOfferOrder() throws InterruptedException {
        InMemoryFrontier frontier = new InMemoryFrontier(2);
        frontier.offer(HOME, 0);
        frontier.offer(ABOUT, 1);

        assertThat(frontier.poll(Duration.ZERO)).hasValue(new CrawlTask(HOME, 0));
        assertThat(frontier.poll(Duration.ZERO)).hasValue(new CrawlTask(ABOUT, 1));
        assertThat(frontier.poll(Duration.ZERO)).isEmpty();
    }

    @Test
    void shouldAcceptOnlyOneOfferWhenTwoThreadsSubmitTheSameUrl() throws InterruptedException {
        InMemoryFrontier frontier = new InMemoryFrontier(1);
        CountDownLatch start = new CountDownLatch(2);
        AtomicInteger accepted = new AtomicInteger();

        Thread first = Thread.ofVirtual().start(() -> offerWhenReady(frontier, start, accepted));
        Thread second = Thread.ofVirtual().start(() -> offerWhenReady(frontier, start, accepted));
        first.join();
        second.join();

        assertThat(accepted).hasValue(1);
        assertThat(frontier.poll(Duration.ZERO)).hasValue(new CrawlTask(HOME, 0));
        assertThat(frontier.poll(Duration.ZERO)).isEmpty();
    }

    @Test
    void shouldRejectNegativeMaxDepth() {
        assertThatIllegalArgumentException().isThrownBy(() -> new InMemoryFrontier(-1));
    }

    @Test
    void shouldReturnEmptyWhenPollTimesOut() throws InterruptedException {
        InMemoryFrontier frontier = new InMemoryFrontier(1);

        Optional<CrawlTask> result = frontier.poll(Duration.ofMillis(20));

        assertThat(result).isEmpty();
    }

    private static void offerWhenReady(InMemoryFrontier frontier, CountDownLatch start, AtomicInteger accepted) {
        start.countDown();
        await(start);
        if (frontier.offer(HOME, 0)) {
            accepted.incrementAndGet();
        }
    }

    private static void await(CountDownLatch latch) {
        try {
            latch.await();
        } catch (InterruptedException interrupted) {
            Thread.currentThread().interrupt();
        }
    }
}

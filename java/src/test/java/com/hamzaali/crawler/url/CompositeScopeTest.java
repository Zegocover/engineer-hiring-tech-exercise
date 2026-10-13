package com.hamzaali.crawler.url;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatIllegalArgumentException;

import java.net.URI;
import java.util.List;
import org.junit.jupiter.api.Test;

class CompositeScopeTest {

    private static final URI HOME = URI.create("https://example.com/");
    private static final URI SECRET = URI.create("https://example.com/secret");

    @Test
    void shouldAllowOnlyWhenEveryPartAllows() {
        CrawlScope host = new SameHostScope(HOME);
        CrawlScope robots = new RobotsTxtScope(List.of("/secret"));
        CrawlScope scope = CompositeScope.of(host, robots);

        assertThat(scope.allows(HOME)).isTrue();
        assertThat(scope.allows(SECRET)).isFalse();
        assertThat(scope.allows(URI.create("https://other.example/"))).isFalse();
    }

    @Test
    void shouldRejectAnEmptyComposition() {
        assertThatIllegalArgumentException().isThrownBy(() -> new CompositeScope(List.of()));
    }
}

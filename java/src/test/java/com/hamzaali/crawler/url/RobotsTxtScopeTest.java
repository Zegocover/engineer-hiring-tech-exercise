package com.hamzaali.crawler.url;

import static org.assertj.core.api.Assertions.assertThat;

import java.net.URI;
import org.junit.jupiter.api.Test;

class RobotsTxtScopeTest {

    private static final URI HOME = URI.create("https://example.com/");
    private static final URI SECRET = URI.create("https://example.com/secret");
    private static final URI SECRET_PAGE = URI.create("https://example.com/secret/page");
    private static final URI ABOUT = URI.create("https://example.com/about");

    @Test
    void shouldAllowEverythingWhenTheFileIsEmpty() {
        RobotsTxtScope scope = RobotsTxtScope.parse("", "ZegoCrawler/0.1");

        assertThat(scope.allows(HOME)).isTrue();
        assertThat(scope.allows(SECRET)).isTrue();
    }

    @Test
    void shouldDisallowPathsListedForAllAgents() {
        RobotsTxtScope scope = RobotsTxtScope.parse("""
                User-agent: *
                Disallow: /secret
                """, "ZegoCrawler/0.1");

        assertThat(scope.allows(HOME)).isTrue();
        assertThat(scope.allows(ABOUT)).isTrue();
        assertThat(scope.allows(SECRET)).isFalse();
        assertThat(scope.allows(SECRET_PAGE)).isFalse();
    }

    @Test
    void shouldPreferAMatchingUserAgentGroupOverTheWildcard() {
        RobotsTxtScope scope = RobotsTxtScope.parse("""
                User-agent: *
                Disallow: /

                User-agent: ZegoCrawler
                Disallow: /secret
                """, "ZegoCrawler/0.1");

        assertThat(scope.allows(HOME)).isTrue();
        assertThat(scope.allows(SECRET)).isFalse();
    }

    @Test
    void shouldTreatAnEmptyDisallowAsAllowAllForThatGroup() {
        RobotsTxtScope scope = RobotsTxtScope.parse("""
                User-agent: ZegoCrawler
                Disallow:

                User-agent: *
                Disallow: /
                """, "ZegoCrawler/0.1");

        assertThat(scope.allows(HOME)).isTrue();
        assertThat(scope.allows(SECRET)).isTrue();
    }

    @Test
    void shouldIgnoreComments() {
        RobotsTxtScope scope = RobotsTxtScope.parse("""
                User-agent: * # everyone
                Disallow: /secret # private
                """, "ZegoCrawler/0.1");

        assertThat(scope.allows(SECRET)).isFalse();
        assertThat(scope.allows(ABOUT)).isTrue();
    }
}

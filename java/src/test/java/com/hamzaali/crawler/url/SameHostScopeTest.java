package com.hamzaali.crawler.url;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatIllegalArgumentException;

import java.net.URI;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

class SameHostScopeTest {

    private final SameHostScope scope = new SameHostScope(URI.create("https://example.com/start"));

    @ParameterizedTest
    @ValueSource(
            strings = {
                "https://example.com/",
                "https://EXAMPLE.COM/about",
                "http://example.com/about",
                "https://example.com:8443/about",
            })
    void shouldAllowHttpUrlWhenHostMatchesExactly(String candidate) {
        assertThat(scope.allows(URI.create(candidate))).isTrue();
    }

    @ParameterizedTest
    @ValueSource(
            strings = {
                "https://sub.example.com/",
                "https://www.example.com/",
                "https://example.com.attacker.test/",
                "https://another-example.com/",
                "ftp://example.com/file",
                "/relative/path",
            })
    void shouldRejectUrlWhenHostDoesNotMatchExactly(String candidate) {
        assertThat(scope.allows(URI.create(candidate))).isFalse();
    }

    @ParameterizedTest
    @ValueSource(strings = {"ftp://example.com", "/relative/path"})
    void shouldRejectSeedWhenItIsNotAnAbsoluteHttpUrl(String seed) {
        assertThatIllegalArgumentException().isThrownBy(() -> new SameHostScope(URI.create(seed)));
    }

    @Test
    void shouldRejectSeedWhenItIsNull() {
        assertThatIllegalArgumentException().isThrownBy(() -> new SameHostScope(null));
    }

    @Test
    void shouldRejectCandidateWhenItIsNull() {
        assertThat(scope.allows(null)).isFalse();
    }
}

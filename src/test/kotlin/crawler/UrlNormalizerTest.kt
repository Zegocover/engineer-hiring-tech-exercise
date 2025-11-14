package crawler

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Test
import org.junit.jupiter.params.ParameterizedTest
import org.junit.jupiter.params.provider.Arguments
import org.junit.jupiter.params.provider.MethodSource
import java.net.URI
import java.util.stream.Stream

class UrlNormalizerTest {

    private val normalizer: UrlNormalizer = DefaultUrlNormalizer()
    private val base = URI("https://example.com/path/")

    @Test
    fun `normalize absolute url`() {
        val input = "https://example.com/abc"
        val expected = "https://example.com/abc"
        val result = normalizer.normalize(base, input)
        assertEquals(expected, result.toString())
    }

    @Test
    fun `normalize relative url`() {
        val input = "../other"
        val expected = "https://example.com/other"
        val result = normalizer.normalize(base, input)
        assertEquals(expected, result.toString())
    }

    @Test
    fun `normalize invalid url returns null`() {
        val input = "http://exa mple.com"
        val result = normalizer.normalize(base, input)
        assertNull(result)
    }

    @ParameterizedTest
    @MethodSource("absoluteUrls")
    fun `parameterized absolute url tests`(input: String, expected: String) {
        val result = normalizer.normalize(base, input)
        assertEquals(expected, result.toString())
    }

    @ParameterizedTest
    @MethodSource("relativeUrls")
    fun `parameterized relative url tests`(input: String, expected: String) {
        val result = normalizer.normalize(base, input)
        assertEquals(expected, result.toString())
    }

    @ParameterizedTest
    @MethodSource("invalidUrls")
    fun `parameterized invalid url tests`(input: String) {
        val result = normalizer.normalize(base, input)
        assertNull(result)
    }

    companion object {
        @JvmStatic
        fun absoluteUrls(): Stream<Arguments> = Stream.of(
            Arguments.of("https://example.com/abc", "https://example.com/abc"),
            Arguments.of("https://example.com/xyz?q=1", "https://example.com/xyz")
        )

        @JvmStatic
        fun relativeUrls(): Stream<Arguments> = Stream.of(
            Arguments.of("../other", "https://example.com/other"),
            Arguments.of("./child", "https://example.com/path/child")
        )

        @JvmStatic
        fun invalidUrls(): Stream<Arguments> = Stream.of(
            Arguments.of("http://exa mple.com"),
            Arguments.of("::::://bad_url")
        )
    }
}
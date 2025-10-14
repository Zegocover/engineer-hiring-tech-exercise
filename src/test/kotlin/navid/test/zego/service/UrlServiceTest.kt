package navid.test.zego.service

import org.junit.Assert.assertThrows
import org.junit.jupiter.api.Assertions.*
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test

class UrlServiceTest {

    private lateinit var service: UrlService

    @BeforeEach
    fun setup() {
        service = UrlService()
    }

    @Test
    fun `should return normalized url without trailing slash`() {
        val result = service.normalize("https://example.com/test/")
        assertEquals("https://example.com/test", result)
    }

    @Test
    fun `should throw if host is missing`() {
        val exception = assertThrows(IllegalArgumentException::class.java) {
            service.normalize("https:///path")
        }
        assertTrue(exception.message!!.contains("URL is not a valid public url"))
    }

    @Test
    fun `should throw if not a valid public url`() {
        val exception = assertThrows(IllegalArgumentException::class.java) {
            service.normalize("http://localhost/test")
        }
        assertTrue(exception.message!!.contains("URL is not a valid public url"))
    }

    @Test
    fun `should allow localhost when allowNonPublicHost is true`() {
        val result = service.normalize("http://localhost/test", allowNonPublicHost = true)
        assertEquals("http://localhost/test", result)
    }

    @Test
    fun `should return correct host`() {
        val domain = service.extractDomain("https://sub.example.com/path")
        assertEquals("sub.example.com", domain)
    }

    @Test
    fun `should return true for same domain`() {
        val result = service.isSameDomain("https://example.com/test", "example.com")
        assertTrue(result)
    }

    @Test
    fun `should return false for different domains`() {
        val result = service.isSameDomain("https://other.com/test", "example.com")
        assertFalse(result)
    }

    @Test
    fun `should return false when URL is invalid`() {
        val result = service.isSameDomain("not a url", "example.com")
        assertFalse(result)
    }

    @Test
    fun `should return true for valid public domain`() {
        val result = service.isValidPublicUrl("https://openai.com")
        assertTrue(result)
    }

    @Test
    fun `should return false for localhost`() {
        val result = service.isValidPublicUrl("http://localhost")
        assertFalse(result)
    }

    @Test
    fun `should return false for malformed url`() {
        val result = service.isValidPublicUrl("not-a-url")
        assertFalse(result)
    }
}
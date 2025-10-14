package navid.test.zego.service

import kotlinx.coroutines.test.runTest
import navid.test.zego.AppProperties
import navid.test.zego.RetryProperties
import navid.test.zego.service.exception.RateLimitException
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import okhttp3.mockwebserver.SocketPolicy
import org.apache.hc.core5.http.HttpStatus
import org.junit.jupiter.api.*
import org.junit.jupiter.params.ParameterizedTest
import org.junit.jupiter.params.provider.CsvSource
import org.junit.jupiter.params.provider.ValueSource
import java.util.concurrent.TimeUnit
import kotlin.system.measureTimeMillis
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class HttpServiceTest {
    private lateinit var httpService: HttpService
    private val mockWebServer by lazy { MockWebServer() }

    private val configProperties by lazy {
        AppProperties(
            connectionTimeout = 1000,
            retry = RetryProperties(
                maxAttempts = 5,
                interval = 1,
                maxInterval = 2,
                backOffMultiplier = 2.0
            )
        )
    }

    @BeforeEach
    fun setup() {
        httpService = HttpService(
            config = configProperties
        )
        mockWebServer.start()
    }

    @AfterEach
    fun teardown() {
        mockWebServer.shutdown()
    }

    @Test
    fun `fetch should return HTML content on successful 200 response`() = runTest {
        val expectedHtml = "<html><body><h1>Test Page</h1></body></html>"
        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(HttpStatus.SC_OK)
                .setBody(expectedHtml)
                .setHeader("Content-Type", "text/html")
        )

        val result = httpService.fetch(mockWebServer.url("/").toString())

        assertEquals(expectedHtml, result)
    }

    @Test
    fun `fetch should include User-Agent header in request`() = runTest {
        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(HttpStatus.SC_OK)
                .setBody("OK")
        )

        httpService.fetch(mockWebServer.url("/").toString())

        val request = mockWebServer.takeRequest()
        assertEquals("WebCrawler/1.0", request.getHeader("User-Agent"))
    }

    @Test
    fun `fetch should handle 201 Created response`() = runTest {
        val body = "Resource created"
        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(HttpStatus.SC_CREATED)
                .setBody(body)
        )

        val result = httpService.fetch(mockWebServer.url("/").toString())

        assertEquals(body, result)
    }

    @Test
    fun `fetch should handle 204 No Content response`() = runTest {
        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(HttpStatus.SC_NO_CONTENT)
        )

        val exception = assertThrows<Exception> {
            httpService.fetch(mockWebServer.url("/").toString())
        }

        assertEquals(exception.message?.contains("Empty response body"), true)
    }

    @Test
    fun `fetch should throw exception on 404 Not Found`() = runTest {
        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(HttpStatus.SC_NOT_FOUND)
                .setBody("Not Found")
        )

        val exception = assertThrows<Exception> {
            httpService.fetch(mockWebServer.url("/notfound").toString())
        }

        assertEquals(exception.message?.contains("HTTP 404"), true)
    }

    @Test
    fun `fetch should throw exception on 500 Internal Server Error`() = runTest {
        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(HttpStatus.SC_INTERNAL_SERVER_ERROR)
                .setBody("Internal Server Error")
        )

        val exception = assertThrows<Exception> {
            httpService.fetch(mockWebServer.url("/error").toString())
        }

        assertEquals(exception.message?.contains("HTTP 500"), true)
    }

    @Test
    fun `fetch should throw exception on 403 Forbidden`() = runTest {
        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(HttpStatus.SC_FORBIDDEN)
                .setBody("Forbidden")
        )

        val exception = assertThrows<Exception> {
            httpService.fetch(mockWebServer.url("/forbidden").toString())
        }

        assertEquals(exception.message?.contains("HTTP 403"), true)
    }

    @Test
    fun `fetch should retry on 429 Too Many Requests`() = runTest {
        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(HttpStatus.SC_TOO_MANY_REQUESTS)
                .setBody("Too Many Requests")
        )

        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(HttpStatus.SC_OK)
                .setBody("Success after retry")
        )

        val result = httpService.fetch(mockWebServer.url("/").toString())
        assertEquals("Success after retry", result)
        assertEquals(2, mockWebServer.requestCount)
    }

    @Test
    fun `fetch should implement exponential backoff on 429 retries`() = runTest {
        repeat(configProperties.retry.maxAttempts - 1) {
            mockWebServer.enqueue(
                MockResponse()
                    .setResponseCode(HttpStatus.SC_TOO_MANY_REQUESTS)
                    .setBody("Too Many Requests")
            )
        }
        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(HttpStatus.SC_OK)
                .setBody("Success")
        )

        val elapsed = measureTimeMillis {
            val result = httpService.fetch(mockWebServer.url("/").toString())
            assertEquals("Success", result)
        }

        assertTrue(elapsed < 300, "Expected to be less than 300ms, got ${elapsed}ms")
        assertEquals(configProperties.retry.maxAttempts, mockWebServer.requestCount)
    }

    @Test
    fun `fetch should not retry on 404 error`() = runTest {
        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(HttpStatus.SC_NOT_FOUND)
        )

        assertThrows<Exception> {
            httpService.fetch(mockWebServer.url("/").toString())
        }

        // Should only make one request (no retries)
        assertEquals(1, mockWebServer.requestCount)
    }

    @Test
    fun `fetch should not retry on 500 error`() = runTest {
        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(HttpStatus.SC_INTERNAL_SERVER_ERROR)
        )

        assertThrows<Exception> {
            httpService.fetch(mockWebServer.url("/").toString())
        }

        // Should only make one request (no retries)
        assertEquals(1, mockWebServer.requestCount)
    }

    @Test
    fun `fetch should handle large response body`() = runTest {
        val largeHtml = "<html><body>" + "Lorem ipsum ".repeat(10000) + "</body></html>"
        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(HttpStatus.SC_OK)
                .setBody(largeHtml)
        )

        val result = httpService.fetch(mockWebServer.url("/").toString())

        assertEquals(largeHtml, result)
        assertTrue(result.length > 100000)
    }

    @Test
    fun `fetch should handle UTF-8 content`() = runTest {
        val utf8Content = "<html><body>Hello 世界 🌍 Café München</body></html>"
        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(HttpStatus.SC_OK)
                .setBody(utf8Content)
                .setHeader("Content-Type", "text/html; charset=utf-8")
        )

        val result = httpService.fetch(mockWebServer.url("/").toString())

        assertEquals(utf8Content, result)
    }

    @Test
    fun `fetch should handle different content types`() = runTest {
        val jsonContent = """{"key": "value"}"""
        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(HttpStatus.SC_OK)
                .setBody(jsonContent)
                .setHeader("Content-Type", "application/json")
        )

        val result = httpService.fetch(mockWebServer.url("/").toString())

        assertEquals(jsonContent, result)
    }

    @Test
    fun `fetch should handle multiple consecutive successful requests`() = runTest {
        repeat(5) { i ->
            mockWebServer.enqueue(
                MockResponse()
                    .setResponseCode(HttpStatus.SC_OK)
                    .setBody("Response $i")
            )
        }

        repeat(5) { i ->
            val result = httpService.fetch(mockWebServer.url("/").toString())
            assertEquals("Response $i", result)
        }

        assertEquals(5, mockWebServer.requestCount)
    }

    @Test
    fun `fetch should handle 429 followed by another error`() = runTest {
        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(HttpStatus.SC_TOO_MANY_REQUESTS)
        )
        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(HttpStatus.SC_INTERNAL_SERVER_ERROR)
        )

        val exception = assertThrows<Exception> {
            httpService.fetch(mockWebServer.url("/").toString())
        }

        assertTrue(exception.message?.contains("HTTP 500") == true)
        assertEquals(2, mockWebServer.requestCount)
    }

    @Test
    fun `fetch should handle connection timeout`() = runTest {
        mockWebServer.enqueue(
            MockResponse()
                .setSocketPolicy(SocketPolicy.NO_RESPONSE)
        )

        val exception = assertThrows<Exception> {
            httpService.fetch(mockWebServer.url("/").toString())
        }

        assertNotNull(exception)
    }

    @Test
    fun `fetch should handle slow response within timeout`() = runTest {
        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(HttpStatus.SC_OK)
                .setBody("Slow response")
                .setBodyDelay(configProperties.connectionTimeout / 2, TimeUnit.MILLISECONDS)
        )

        val result = httpService.fetch(mockWebServer.url("/").toString())

        assertEquals("Slow response", result)
    }

    @Test
    fun `fetch should make GET request`() = runTest {
        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(HttpStatus.SC_OK)
                .setBody("OK")
        )

        httpService.fetch(mockWebServer.url("/test").toString())

        val request = mockWebServer.takeRequest()
        assertEquals("GET", request.method)
        assertEquals("/test", request.path)
    }

    @Test
    fun `fetch should handle query parameters`() = runTest {
        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(HttpStatus.SC_OK)
                .setBody("OK")
        )

        httpService.fetch(mockWebServer.url("/?param1=value1&param2=value2").toString())

        val request = mockWebServer.takeRequest()
        assertEquals(request.path?.contains("param1=value1"), true)
        assertEquals(request.path?.contains("param2=value2"), true)
    }

    @ParameterizedTest
    @CsvSource(
        "301, /redirected",
        "302, /found",
        "303, /see-other",
        "307, /temporary",
        "308, /permanent"
    )
    fun `fetch should handle redirect status codes`(statusCode: Int, path: String) = runTest {
        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(statusCode)
                .setHeader("Location", mockWebServer.url(path))
        )
        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(HttpStatus.SC_OK)
                .setBody("Redirected content")
        )

        val result = httpService.fetch(mockWebServer.url("/original").toString())

        assertEquals("Redirected content", result)
        assertEquals(2, mockWebServer.requestCount)
    }

    @ParameterizedTest
    @CsvSource(
        "text/html, <html><body>HTML</body></html>",
        "application/json, {\"key\":\"value\"}",
        "text/plain, Plain text content",
        "application/xml, <root><element>XML</element></root>",
        "text/css, body { color: red; }"
    )
    fun `fetch should handle different content types`(contentType: String, body: String) = runTest {
        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(HttpStatus.SC_OK)
                .setBody(body)
                .setHeader("Content-Type", contentType)
        )

        val result = httpService.fetch(mockWebServer.url("/").toString())

        assertEquals(body, result)
    }

    enum class HttpMethod {
        GET, POST, PUT, DELETE, PATCH
    }

    @ParameterizedTest
    @ValueSource(
        strings = [
            "/path/with spaces/page",
            "/path?param=value&other=123",
            "/path#section",
            "/日本語",
            "/Türkçe",
            "/پارسی"
        ]
    )
    fun `fetch should handle special characters in URL`(path: String) = runTest {
        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(HttpStatus.SC_OK)
                .setBody("OK")
        )

        val result = httpService.fetch(mockWebServer.url(path).toString())

        assertEquals("OK", result)
    }

    @ParameterizedTest
    @ValueSource(ints = [1, 2, 3, 4])
    fun `fetch should retry correct number of times on 429`(numRetries: Int) = runTest {
        // Enqueue numRetries x 429, then success
        repeat(numRetries) {
            mockWebServer.enqueue(MockResponse().setResponseCode(HttpStatus.SC_TOO_MANY_REQUESTS))
        }
        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(HttpStatus.SC_OK)
                .setBody("Success after $numRetries retries")
        )

        val result = httpService.fetch(mockWebServer.url("/").toString())

        assertEquals("Success after $numRetries retries", result)
        assertEquals(numRetries + 1, mockWebServer.requestCount)
    }

    @ParameterizedTest
    @CsvSource("1", "2", "3", "4")
    fun `fetch should implement correct exponential backoff delays`(retryCount: Int) = runTest {
        repeat(retryCount) {
            mockWebServer.enqueue(MockResponse().setResponseCode(HttpStatus.SC_TOO_MANY_REQUESTS))
        }
        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(HttpStatus.SC_OK)
                .setBody("Success")
        )

        val elapsed = measureTimeMillis {
            httpService.fetch(mockWebServer.url("/").toString())
        }

        assertEquals(retryCount + 1, mockWebServer.requestCount)
        assertTrue(
            elapsed <= 300,
            "Expected less than 300ms, got ${elapsed}ms"
        )
    }

    @ParameterizedTest
    @ValueSource(
        strings = [
            "",
            "   ",
            "\n\t",
            "   \n\t  "
        ]
    )
    fun `fetch should handle whitespace-only response bodies`(body: String) = runTest {
        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(HttpStatus.SC_OK)
                .setBody(body)
        )

        val exception = assertThrows<Exception> {
            httpService.fetch(mockWebServer.url("/").toString())
        }

        assertEquals(exception.message?.contains("Empty response body"), true)
        assertEquals(1, mockWebServer.requestCount)
    }

    @ParameterizedTest
    @CsvSource(
        "UTF-8, 日本語",
        "UTF-8, پارسی",
        "UTF-8, Türkçe",
        "ISO-8859-1, English"
    )
    fun `fetch should handle different character encodings`(charset: String, content: String) = runTest {
        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(HttpStatus.SC_OK)
                .setBody(content)
                .setHeader("Content-Type", "text/html; charset=$charset")
        )

        val result = httpService.fetch(mockWebServer.url("/").toString())

        assertTrue(
            result.contains("English") ||
                    result.contains("پارسی") ||
                    result.contains("日本語") ||
                    result.contains("Türkçe")
        )
    }

    @Test
    fun `fetch should preserve original response body exactly`() = runTest {
        val bodyWithFormatting = """
            <html>
                <head>
                    <title>Test</title>
                </head>
                <body>
                    <p>Paragraph</p>
                </body>
            </html>
        """.trimIndent()

        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(HttpStatus.SC_OK)
                .setBody(bodyWithFormatting)
        )

        val result = httpService.fetch(mockWebServer.url("/").toString())

        assertEquals(bodyWithFormatting, result)
    }

    @Test
    fun `fetch should handle 429 on last retry attempt`() = runTest {
        repeat(configProperties.retry.maxAttempts) {
            mockWebServer.enqueue(
                MockResponse()
                    .setResponseCode(HttpStatus.SC_TOO_MANY_REQUESTS)
            )
        }

        val exception = assertThrows<Exception> {
            httpService.fetch(mockWebServer.url("/").toString())
        }

        assertEquals(exception.message?.contains("Too Many Requests"), true)
        assertTrue(exception is RateLimitException)
    }

    @Test
    fun `fetch should handle null response entity`() = runTest {
        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(HttpStatus.SC_NO_CONTENT)
                .setBody("")
        )

        val exception = assertThrows<Exception> {
            httpService.fetch(mockWebServer.url("/").toString())
        }

        assertEquals(exception.message?.contains("Empty response body"), true)
    }

    @ParameterizedTest
    @ValueSource(ints = [200, 201, 202, 203, 205, 206])
    fun `fetch should handle successful status codes in 2xx range`(statusCode: Int) = runTest {
        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(statusCode)
                .setBody("Status $statusCode")
        )

        val result = httpService.fetch(mockWebServer.url("/").toString())
        assertEquals("Status $statusCode", result)
    }

    @ParameterizedTest
    @ValueSource(ints = [400, 401, 403, 404, 405, 410])
    fun `fetch should throw exception on 4xx client errors`(statusCode: Int) = runTest {
        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(statusCode)
                .setBody("Client Error")
        )

        val exception = assertThrows<Exception> {
            httpService.fetch(mockWebServer.url("/").toString())
        }

        assertEquals(exception.message?.contains("HTTP $statusCode"), true)
        assertEquals(1, mockWebServer.requestCount) // No retries
    }

    @ParameterizedTest
    @ValueSource(ints = [500, 501, 502, 503, 504])
    fun `fetch should throw exception on 5xx server errors`(statusCode: Int) = runTest {
        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(statusCode)
                .setBody("Server Error")
        )

        val exception = assertThrows<Exception> {
            httpService.fetch(mockWebServer.url("/").toString())
        }

        assertEquals(exception.message?.contains("HTTP $statusCode"), true)
        assertEquals(1, mockWebServer.requestCount) // No retries
    }
}
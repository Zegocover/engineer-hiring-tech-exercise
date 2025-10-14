package navid.test.zego.service

import navid.test.zego.AppProperties
import navid.test.zego.service.exception.RateLimitException
import org.apache.hc.core5.http.HttpHeaders
import org.apache.hc.core5.http.HttpStatus
import org.springframework.retry.policy.SimpleRetryPolicy
import org.springframework.retry.support.RetryTemplateBuilder
import org.springframework.stereotype.Service
import java.net.URI
import java.net.http.HttpClient
import java.net.http.HttpRequest
import java.net.http.HttpResponse
import java.time.Duration

/**
 * HTTP client service with connection pooling and timeouts.
 */
@Service
class HttpService(
    private val config: AppProperties
) {

    suspend fun fetch(url: String): String {
        val retryTemplate = RetryTemplateBuilder()
            .exponentialBackoff(
                config.retry.interval,
                config.retry.backOffMultiplier,
                config.retry.maxInterval
            )
            .build()
            .apply {
                setRetryPolicy(
                    SimpleRetryPolicy(
                        config.retry.maxAttempts,
                        mapOf(
                            RateLimitException::class.java to true
                        )
                    )
                )
            }

        return retryTemplate.execute<String, RateLimitException> {
            fetchBlockingInternal(url)
        }
    }

    private fun fetchBlockingInternal(url: String): String {
        val client = HttpClient.newBuilder()
            .followRedirects(HttpClient.Redirect.ALWAYS)
            .connectTimeout(Duration.ofMillis(config.connectionTimeout))
            .build()

        val request = HttpRequest
            .newBuilder()
            .GET()
            .timeout(Duration.ofMillis(config.connectionTimeout))
            .uri(URI.create(url))
            .header(HttpHeaders.USER_AGENT, "WebCrawler/1.0")
            .build()

        val response = client
            .send(
                request,
                HttpResponse.BodyHandlers.ofString()
            )

        val statusCode = response.statusCode()
        if (statusCode == HttpStatus.SC_TOO_MANY_REQUESTS) {
            throw RateLimitException()
        }

        if (statusCode !in (200..299)) {
            throw RuntimeException("HTTP $statusCode")
        }

        val body = response.body()
        if (body.isNullOrBlank()) {
            throw RuntimeException("Empty response body")
        }
        return body
    }
}

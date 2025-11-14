package crawler

import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.every
import io.mockk.mockk
import kotlinx.coroutines.test.runTest
import java.net.URI
import kotlin.test.Test

class CrawlerTest {

    private val fetcher: Fetcher = mockk()
    private val parser: LinkParser = mockk()
    private val normalizer: UrlNormalizer = mockk()

    @Test
    fun `crawl follows links breadth first and fetches each only once`() = runTest {
        val crawler = Crawler(fetcher, parser, normalizer, maxConcurrency = 4)

        coEvery { fetcher.fetch("https://example.com") } returns "<a href=\"/p1\">1</a>"
        coEvery { fetcher.fetch("https://example.com/p1") } returns "<a href=\"/p2\">2</a>"
        coEvery { fetcher.fetch("https://example.com/p2") } returns "<p>done</p>"

        every { parser.parseLinks(any(), any()) } answers {
            when (secondArg<URI>().path) {
                "/", "" -> listOf("/p1")
                "/p1" -> listOf("/p2")
                "/p2" -> emptyList()
                else -> emptyList()
            }
        }

        every { normalizer.normalize(any(), any()) } answers {
            val base = firstArg<URI>()
            val link = secondArg<String>()
            base.resolve(link).normalize()
        }

        crawler.crawl("https://example.com")

        coVerify(exactly = 1) { fetcher.fetch("https://example.com") }
        coVerify(exactly = 1) { fetcher.fetch("https://example.com/p1") }
        coVerify(exactly = 1) { fetcher.fetch("https://example.com/p2") }
    }
}
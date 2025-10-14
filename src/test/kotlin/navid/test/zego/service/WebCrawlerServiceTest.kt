package navid.test.zego.service

import io.mockk.*
import kotlinx.coroutines.test.runTest
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test

class WebCrawlerServiceTest {

    private lateinit var urlService: UrlService
    private lateinit var httpService: HttpService
    private lateinit var htmlParserService: HtmlParserService
    private lateinit var crawler: WebCrawlerService

    @BeforeEach
    fun setup() {
        urlService = mockk()
        httpService = mockk()
        htmlParserService = mockk()
        crawler = WebCrawlerService(urlService, httpService, htmlParserService)
    }

    @Test
    fun `crawl should visit pages within same domain only`() = runTest {
        val baseUrl = "https://example.com"

        every { urlService.normalize(baseUrl) } returns baseUrl
        every { urlService.extractDomain(baseUrl) } returns "example.com"
        every { urlService.isSameDomain(any(), "example.com") } answers {
            val link = firstArg<String>()
            link.contains("example.com")
        }

        coEvery { httpService.fetch(baseUrl) } returns "<a href='$baseUrl/page1'></a>"
        coEvery { htmlParserService.extractLinks(any(), any()) } returns listOf(
            "$baseUrl/page1",
            "https://other.com/page2"
        )

        coEvery { httpService.fetch("$baseUrl/page1") } returns "<html></html>"
        coEvery { htmlParserService.extractLinks("<html></html>", "$baseUrl/page1") } returns emptyList()

        crawler.crawl(baseUrl, maxConcurrentRequests = 2)

        coVerify(exactly = 1) { httpService.fetch(baseUrl) }
        coVerify(exactly = 1) { httpService.fetch("$baseUrl/page1") }

        verify(exactly = 1) { urlService.isSameDomain("$baseUrl/page1", "example.com") }
        verify(exactly = 1) { urlService.isSameDomain("https://other.com/page2", "example.com") }
    }
}
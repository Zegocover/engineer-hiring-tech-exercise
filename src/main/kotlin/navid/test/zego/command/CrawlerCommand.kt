package navid.test.zego.command

import kotlinx.coroutines.runBlocking
import navid.test.zego.service.WebCrawlerService
import org.springframework.boot.CommandLineRunner
import org.springframework.stereotype.Component
import kotlin.system.measureTimeMillis

/**
 * Spring Shell command interface for the web crawler.
 */
@Component
class CrawlerCommand(
    private val webCrawlerService: WebCrawlerService
) : CommandLineRunner {

    override fun run(vararg args: String) {
        if (args.isEmpty()) {
            println("Please provide a url and optionally the number of concurrent request like `https://example.com 50`")
            return
        }
        val url = args[0]
        val maxConcurrent = args.getOrNull(1)?.toIntOrNull() ?: 50
        val elapsed = measureTimeMillis {
            runBlocking {
                webCrawlerService.crawl(url, maxConcurrent)
            }
        }
        println("Crawling completed in ${elapsed}ms")
    }

}
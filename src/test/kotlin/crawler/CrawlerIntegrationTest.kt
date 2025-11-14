package crawler

import io.ktor.http.*
import io.ktor.server.application.*
import io.ktor.server.engine.*
import io.ktor.server.netty.*
import io.ktor.server.response.*
import io.ktor.server.routing.*
import kotlinx.coroutines.test.runTest
import kotlin.test.Test

class CrawlerIntegrationTest {

    @Test
    fun `full crawl end to end`() = runTest {
        val server = embeddedServer(Netty, port = 8089) {
            routing {
                get("/") { call.respondText("<a href=\"/a\">A</a>") }
                get("/a") { call.respondText("<a href=\"/b\">B</a>") }
                get("/b") { call.respondText("done") }
            }
        }.start()

        val crawler = Crawler(
            fetcher = HttpFetcher(),
            parser = JsoupLinkParser(),
            normalizer = DefaultUrlNormalizer(),
            maxConcurrency = 8
        )

        crawler.crawl("http://localhost:8089/")

        server.stop()
    }
}
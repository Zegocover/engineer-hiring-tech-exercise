package crawler

import kotlinx.coroutines.runBlocking

fun main(args: Array<String>) = runBlocking {
    if (args.isEmpty()) {
        println("Usage: crawler <base-url>")
        return@runBlocking
    }

    val crawler = Crawler(
        fetcher = HttpFetcher(),
        parser = JsoupLinkParser(),
        normalizer = DefaultUrlNormalizer()
    )

    crawler.crawl(args[0])
}
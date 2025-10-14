package navid.test.zego.service

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope
import org.springframework.stereotype.Service
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.ConcurrentLinkedDeque

@Service
class WebCrawlerService(
    private val urlService: UrlService,
    private val httpService: HttpService,
    private val htmlParserService: HtmlParserService
) {
    suspend fun crawl(baseUrl: String, maxConcurrentRequests: Int = 50) = coroutineScope {
        val visited = ConcurrentHashMap.newKeySet<String>()

        val normalizedBase = urlService.normalize(baseUrl)
        val baseDomain = urlService.extractDomain(normalizedBase)

        // Did not use logger as I wanted to simply print the string below without any extra info such as date and other stuff
        println(
            """
                
                ----------------------------------------------
                Base URL: $normalizedBase
                Base Domain: $baseDomain
                Max concurrent requests: $maxConcurrentRequests
                -----------------------------------------------
                
            """.trimIndent()
        )

        val queue = ConcurrentLinkedDeque<String>()
        queue.add(normalizedBase)
        visited.add(normalizedBase)

        var totalUrls = 0
        var totalLinks = 0

        while (queue.isNotEmpty()) {
            val batch = mutableListOf<String>()
            while (queue.isNotEmpty() && batch.size < maxConcurrentRequests) {
                batch.add(queue.removeFirst())
            }

            val jobs = batch.map { url ->
                async(Dispatchers.IO) {
                    processUrl(url, baseDomain)
                }
            }

            jobs
                .awaitAll()
                .forEach { result ->
                    totalUrls++
                    totalLinks += result.size
                    result.forEach { newUrl ->
                        if (visited.add(newUrl)) {
                            queue.add(newUrl)
                        }
                    }
                }
        }

        println(
            """
                
                ---------------- Crawl Summary -----------------
                Total pages crawled: $totalUrls
                Total links found: $totalLinks
                Total unique URLs discovered: ${visited.toSet().size}
                -------------------------------------------------
                
            """.trimIndent()
        )
    }

    private suspend fun processUrl(url: String, baseDomain: String): Set<String> = try {
        val html = httpService.fetch(url)
        val links = htmlParserService.extractLinks(html, url)

        // Filter to same domain only
        val sameDomainLinks = links.filter { link ->
            urlService.isSameDomain(link, baseDomain)
        }

        synchronized(System.out) {
            println(url)
            if (sameDomainLinks.isEmpty()) {
                println("   |_ (no links found)")
            } else {
                sameDomainLinks.forEachIndexed { index, link ->
                    val prefix = when (index) {
                        sameDomainLinks.size - 1 -> "|_"
                        else -> "|-"
                    }
                    println("   $prefix $link")
                }
            }
            println()
        }

        sameDomainLinks.toSet()
    } catch (e: Exception) {
        synchronized(System.out) {
            println(url)
            println("   |_ x ERROR: ${e.message}")
            println()
        }
        emptySet()
    }
}
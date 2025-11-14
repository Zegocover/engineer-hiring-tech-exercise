package crawler

import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Semaphore
import java.net.URI
import java.util.concurrent.ConcurrentHashMap

class Crawler(
    private val fetcher: Fetcher,
    private val parser: LinkParser,
    private val normalizer: UrlNormalizer,
    private val maxConcurrency: Int = 64,
) {

    suspend fun crawl(startUrl: String) {
        val root = URI(startUrl)
        val domain = root.host

        val visited = ConcurrentHashMap.newKeySet<String>()
        val queue = ArrayDeque<URI>()

        queue.add(root)
        visited.add(root.toString())

        val semaphore = Semaphore(maxConcurrency)

        coroutineScope {
            launch {
                while (queue.isNotEmpty()) {
                    val url = queue.removeFirst()

                    semaphore.acquire()
                    try {
                        val html = fetcher.fetch(url.toString()) ?: continue

                        val links = parser.parseLinks(html, url)

                        val normalized = links.mapNotNull { normalizer.normalize(url, it) }
                            .filter { it.host == domain }
                            .filter { visited.add(it.toString()) }

                        println("Page: $url")
                        normalized.forEach { println("  → $it") }

                        normalized.forEach { queue.add(it) }

                    } finally {
                        semaphore.release()
                    }
                }
            }
        }
    }
}
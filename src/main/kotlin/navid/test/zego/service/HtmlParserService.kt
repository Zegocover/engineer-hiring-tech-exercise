package navid.test.zego.service

import org.jsoup.Jsoup
import org.springframework.stereotype.Service

/**
 * HTML parsing service using Jsoup.
 */
@Service
class HtmlParserService(
    private val urlService: UrlService
) {
    fun extractLinks(html: String, baseUrl: String): List<String> = Jsoup
        .parse(html, baseUrl)
        .select("a[href]")
        .mapNotNull { element ->
            val href = element.attr("abs:href")
            if (href.isNotBlank()) {
                try {
                    urlService.normalize(href)
                } catch (_: Exception) {
                    null
                }
            } else {
                null
            }
        }
        .distinct()
        .sorted()

}
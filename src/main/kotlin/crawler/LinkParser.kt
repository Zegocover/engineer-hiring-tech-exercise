package crawler

import org.jsoup.Jsoup
import java.net.URI

interface LinkParser {
    fun parseLinks(html: String, base: URI): List<String>
}

class JsoupLinkParser : LinkParser {

    override fun parseLinks(html: String, base: URI): List<String> {
        val doc = Jsoup.parse(html, base.toString())
        return doc.select("a[href]").map { it.attr("href") }
    }
}
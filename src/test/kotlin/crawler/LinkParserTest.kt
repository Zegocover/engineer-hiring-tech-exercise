package crawler

import java.net.URI
import kotlin.test.Test
import kotlin.test.assertEquals

class LinkParserTest {

    private val parser = JsoupLinkParser()
    private val base = URI("https://example.com")

    @Test
    fun `parses all href links`() {
        val html = """
            <html>
              <body>
                <a href="/one">One</a>
                <a href="two">Two</a>
                <a href="http://other.com/page">Other</a>
              </body>
            </html>
        """.trimIndent()

        val links = parser.parseLinks(html, base)

        assertEquals(listOf("/one", "two", "http://other.com/page"), links)
    }

    @Test
    fun `returns empty when no links`() {
        val html = "<html><body>No links here</body></html>"
        assertEquals(emptyList(), parser.parseLinks(html, base))
    }
}
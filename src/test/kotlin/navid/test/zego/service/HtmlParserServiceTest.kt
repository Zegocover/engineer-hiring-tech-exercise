package navid.test.zego.service

import io.mockk.clearAllMocks
import io.mockk.every
import io.mockk.mockk
import io.mockk.verify
import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.Assertions.*
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test

internal class HtmlParserServiceTest {
    private lateinit var htmlParserService: HtmlParserService
    private lateinit var urlService: UrlService

    @BeforeEach
    fun setup() {
        urlService = mockk()
        htmlParserService = HtmlParserService(urlService)

        // Default behavior: normalize returns the input unchanged
        every { urlService.normalize(any()) } answers { firstArg() }
    }

    @AfterEach
    fun teardown() {
        clearAllMocks()
    }

    @Test
    fun `should find all anchor tags with href`() {
        val html = """
            <html>
                <body>
                    <a href="/page1">Page 1</a>
                    <a href="/page2">Page 2</a>
                    <a href="/page3">Page 3</a>
                </body>
            </html>
        """.trimIndent()

        val links = htmlParserService.extractLinks(html, "https://example.com")

        assertEquals(3, links.size)
        assertTrue(links.contains("https://example.com/page1"))
        assertTrue(links.contains("https://example.com/page2"))
        assertTrue(links.contains("https://example.com/page3"))
    }

    @Test
    fun `should ignore anchors without href attribute`() {
        val html = """
            <html>
                <body>
                    <a href="/valid">Valid</a>
                    <a>No href attribute</a>
                    <a name="anchor">Named anchor</a>
                </body>
            </html>
        """.trimIndent()

        val links = htmlParserService.extractLinks(html, "https://example.com")

        assertEquals(1, links.size)
        assertEquals("https://example.com/valid", links.first())
    }

    @Test
    fun `should ignore invalid href attributes`() {
        val html = """
            <html>
                <body>
                    <a href="">Empty</a>
                    <a href="   ">Whitespace only</a>
                    <a href="/valid">Valid</a>
                </body>
            </html>
        """.trimIndent()

        val links = htmlParserService.extractLinks(html, "https://example.com")

        assertEquals(2, links.size)
        assertEquals("https://example.com", links.first())
        assertEquals("https://example.com/valid", links.last())
    }

    @Test
    fun `should handle absolute URLs`() {
        val html = """
            <html>
                <body>
                    <a href="https://example.com/absolute">Absolute</a>
                    <a href="/relative">Relative</a>
                    <a href="https://other.com/external">External</a>
                </body>
            </html>
        """.trimIndent()

        val links = htmlParserService.extractLinks(html, "https://example.com")

        assertEquals(3, links.size)
        assertTrue(links.contains("https://example.com/absolute"))
        assertTrue(links.contains("https://example.com/relative"))
        assertTrue(links.contains("https://other.com/external"))
    }

    @Test
    fun `should handle relative paths correctly`() {
        val html = """
            <html>
                <body>
                    <a href="/absolute/path">Absolute path</a>
                    <a href="relative/path">Relative path</a>
                    <a href="../parent/path">Parent path</a>
                    <a href="./same/path">Same directory</a>
                </body>
            </html>
        """.trimIndent()

        val links = htmlParserService.extractLinks(html, "https://example.com/base/page")

        assertEquals(4, links.size)
        assertTrue(links.contains("https://example.com/absolute/path"))
        assertTrue(links.contains("https://example.com/base/relative/path"))
        assertTrue(links.contains("https://example.com/parent/path"))
        assertTrue(links.contains("https://example.com/base/same/path"))
    }

    @Test
    fun `should remove duplicate URLs`() {
        val html = """
            <html>
                <body>
                    <a href="/page">Link 1</a>
                    <a href="/page">Link 2 (duplicate)</a>
                    <a href="/page">Link 3 (duplicate)</a>
                    <a href="/other">Link 4</a>
                </body>
            </html>
        """.trimIndent()

        val links = htmlParserService.extractLinks(html, "https://example.com")

        assertEquals(2, links.size)
        assertTrue(links.contains("https://example.com/page"))
        assertTrue(links.contains("https://example.com/other"))
    }

    @Test
    fun `should sort results alphabetically`() {
        val html = """
            <html>
                <body>
                    <a href="/zebra">Z</a>
                    <a href="/apple">A</a>
                    <a href="/middle">M</a>
                    <a href="/banana">B</a>
                </body>
            </html>
        """.trimIndent()

        val links = htmlParserService.extractLinks(html, "https://example.com")

        assertEquals(4, links.size)
        assertEquals("https://example.com/apple", links[0])
        assertEquals("https://example.com/banana", links[1])
        assertEquals("https://example.com/middle", links[2])
        assertEquals("https://example.com/zebra", links[3])
    }

    @Test
    fun `should call urlService normalize for each link`() {
        val html = """
            <html>
                <body>
                    <a href="/page1/">Page 1</a>
                    <a href="/page2/">Page 2</a>
                </body>
            </html>
        """.trimIndent()

        every { urlService.normalize(any()) } returns "https://example.com/normalized"

        val links = htmlParserService.extractLinks(html, "https://example.com")

        verify(exactly = 2) { urlService.normalize(any()) }
        assertEquals(1, links.size) // Both normalized to same URL, so deduplicated
        assertEquals("https://example.com/normalized", links.first())
    }

    @Test
    fun `should handle urlService normalize throwing exception`() {
        val html = """
            <html>
                <body>
                    <a href="/valid1">Valid 1</a>
                    <a href="/invalid">Invalid</a>
                    <a href="/valid2">Valid 2</a>
                </body>
            </html>
        """.trimIndent()

        every { urlService.normalize("https://example.com/valid1") } returns "https://example.com/valid1"
        every { urlService.normalize("https://example.com/invalid") } throws IllegalArgumentException("Invalid URL")
        every { urlService.normalize("https://example.com/valid2") } returns "https://example.com/valid2"

        val links = htmlParserService.extractLinks(html, "https://example.com")

        assertEquals(2, links.size)
        assertTrue(links.contains("https://example.com/valid1"))
        assertTrue(links.contains("https://example.com/valid2"))
        assertFalse(links.contains("https://example.com/invalid"))
    }

    @Test
    fun `should handle malformed HTML gracefully`() {
        val html = """
            <html>
                <body>
                    <a href="/page1">Unclosed anchor
                    <a href="/page2">Missing closing body tag
                    <div>
                        <a href="/page3">Nested in unclosed div
        """.trimIndent()

        val links = htmlParserService.extractLinks(html, "https://example.com")

        assertEquals(3, links.size)
        assertTrue(links.contains("https://example.com/page1"))
        assertTrue(links.contains("https://example.com/page2"))
        assertTrue(links.contains("https://example.com/page3"))
    }

    @Test
    fun `should handle special characters in URLs`() {
        val html = """
            <html>
                <body>
                    <a href="/page?param=value&other=123">Query string</a>
                    <a href="/page#section">Fragment</a>
                    <a href="/page?q=hello world">Spaces in query</a>
                    <a href="/path/with spaces/page">Spaces in path</a>
                </body>
            </html>
        """.trimIndent()

        val links = htmlParserService.extractLinks(html, "https://example.com")

        assertEquals(4, links.size)
        assertTrue(links.any { link -> link.contains("param=value") })
        assertTrue(links.any { link -> link.contains("#section") })
    }

    @Test
    fun `should handle different protocols`() {
        val html = """
            <html>
                <body>
                    <a href="http://example.com/page">HTTP</a>
                    <a href="https://example.com/page">HTTPS</a>
                    <a href="ftp://example.com/file">FTP</a>
                    <a href="mailto:test@example.com">Email</a>
                    <a href="javascript:void(0)">JavaScript</a>
                    <a href="tel:+1234567890">Phone</a>
                </body>
            </html>
        """.trimIndent()

        val links = htmlParserService.extractLinks(html, "https://example.com")

        assertEquals(6, links.size)
        assertTrue(links.any { items -> items.startsWith("http://") })
        assertTrue(links.any { items -> items.startsWith("https://") })
        assertTrue(links.any { items -> items.startsWith("ftp://") })
    }

    @Test
    fun `should return empty list for HTML with no anchors`() {
        val html = """
            <html>
                <body>
                    <p>Just text content</p>
                    <div>No links here</div>
                </body>
            </html>
        """.trimIndent()

        val links = htmlParserService.extractLinks(html, "https://example.com")

        assertTrue(links.isEmpty())
    }

    @Test
    fun `should return empty list for empty HTML`() {
        val html = ""

        val links = htmlParserService.extractLinks(html, "https://example.com")

        assertTrue(links.isEmpty())
    }

    @Test
    fun `should handle case-insensitive anchor tags`() {
        val html = """
            <html>
                <body>
                    <a href="/lowercase">Lowercase</a>
                    <A href="/uppercase">Uppercase</A>
                    <A HREF="/all-caps">All caps</A>
                </body>
            </html>
        """.trimIndent()

        val links = htmlParserService.extractLinks(html, "https://example.com")

        assertEquals(3, links.size)
        assertTrue(links.contains("https://example.com/lowercase"))
        assertTrue(links.contains("https://example.com/uppercase"))
        assertTrue(links.contains("https://example.com/all-caps"))
    }

    @Test
    fun `should handle anchors with multiple attributes`() {
        val html = """
            <html>
                <body>
                    <a href="/page" class="link" id="link1" target="_blank" rel="noopener">Link 1</a>
                    <a title="Title" href="/page2" data-attr="value">Link 2</a>
                    <a href="/page3" style="color: blue;">Link 3</a>
                </body>
            </html>
        """.trimIndent()

        val links = htmlParserService.extractLinks(html, "https://example.com")

        assertEquals(3, links.size)
        assertTrue(links.contains("https://example.com/page"))
        assertTrue(links.contains("https://example.com/page2"))
        assertTrue(links.contains("https://example.com/page3"))
    }

    @Test
    fun `should handle nested HTML structure`() {
        val html = """
            <html>
                <body>
                    <div>
                        <nav>
                            <ul>
                                <li><a href="/nav1">Nav 1</a></li>
                                <li><a href="/nav2">Nav 2</a></li>
                            </ul>
                        </nav>
                        <article>
                            <section>
                                <a href="/article">Article link</a>
                            </section>
                        </article>
                    </div>
                </body>
            </html>
        """.trimIndent()

        val links = htmlParserService.extractLinks(html, "https://example.com")

        assertEquals(3, links.size)
        assertTrue(links.contains("https://example.com/nav1"))
        assertTrue(links.contains("https://example.com/nav2"))
        assertTrue(links.contains("https://example.com/article"))
    }

    @Test
    fun `should handle anchors with nested content`() {
        val html = """
            <html>
                <body>
                    <a href="/page1"><span>Nested span</span></a>
                    <a href="/page2"><strong>Bold</strong> and <em>italic</em></a>
                    <a href="/page3">
                        <div>
                            <p>Complex nested structure</p>
                        </div>
                    </a>
                </body>
            </html>
        """.trimIndent()

        val links = htmlParserService.extractLinks(html, "https://example.com")

        assertEquals(3, links.size)
        assertTrue(links.contains("https://example.com/page1"))
        assertTrue(links.contains("https://example.com/page2"))
        assertTrue(links.contains("https://example.com/page3"))
    }

    @Test
    fun `should handle URLs with fragments`() {
        val html = """
            <html>
                <body>
                    <a href="/page#section1">Section 1</a>
                    <a href="/page#section2">Section 2</a>
                    <a href="#local">Local anchor</a>
                </body>
            </html>
        """.trimIndent()

        val links = htmlParserService.extractLinks(html, "https://example.com/base")

        assertEquals(3, links.size)
        assertTrue(links.any { link -> link.contains("#section1") })
        assertTrue(links.any { link -> link.contains("#section2") })
        assertTrue(links.any { link -> link.contains("#local") })
    }

    @Test
    fun `should normalize URLs through urlService`() {
        val html = """
            <html>
                <body>
                    <a href="https://example.com:443/page/">Link</a>
                </body>
            </html>
        """.trimIndent()

        every { urlService.normalize("https://example.com:443/page/") } returns "https://example.com/page"

        val links = htmlParserService.extractLinks(html, "https://example.com")

        verify(exactly = 1) { urlService.normalize("https://example.com:443/page/") }
        assertEquals(1, links.size)
        assertEquals("https://example.com/page", links.first())
    }

    @Test
    fun `should handle data-href attributes being ignored`() {
        val html = """
            <html>
                <body>
                    <a href="/real-link">Real</a>
                    <a data-href="/data-link">Data attribute</a>
                    <div href="/div-href">Div with href</div>
                </body>
            </html>
        """.trimIndent()

        val links = htmlParserService.extractLinks(html, "https://example.com")

        assertEquals(1, links.size)
        assertEquals("https://example.com/real-link", links.first())
    }

    @Test
    fun `should handle international characters in URLs`() {
        val html = """
            <html>
                <body>
                    <a href="/日本語">Japanese</a>
                    <a href="/Türkçe">Turkish</a>
                    <a href="/پارسی">Persian</a>
                </body>
            </html>
        """.trimIndent()

        val links = htmlParserService.extractLinks(html, "https://example.com")

        assertTrue(links.size >= 3)
    }

    @Test
    fun `should handle very long URLs`() {
        val longPath = "/very/long/path/" + "segment/".repeat(100) + "page"
        val html = """
            <html>
                <body>
                    <a href="$longPath">Long URL</a>
                </body>
            </html>
        """.trimIndent()

        val baseUrl = "https://example.com"
        val links = htmlParserService.extractLinks(html, baseUrl)

        assertEquals(1, links.size)
        assertEquals(baseUrl.length + longPath.length, links.first().length)
    }

    @Test
    fun `should handle urlService normalize returning different URL`() {
        val html = """
            <html>
                <body>
                    <a href="/Page">Mixed case</a>
                    <a href="/page/">Trailing slash</a>
                </body>
            </html>
        """.trimIndent()

        every { urlService.normalize(any()) } returns "https://example.com/page"

        val links = htmlParserService.extractLinks(html, "https://example.com")

        assertEquals(1, links.size)
        assertEquals("https://example.com/page", links.first())
        verify(exactly = 2) { urlService.normalize(any()) }
    }

    @Test
    fun `should maintain order after sorting with duplicate removal`() {
        val html = """
            <html>
                <body>
                    <a href="/c">C</a>
                    <a href="/a">A</a>
                    <a href="/b">B</a>
                    <a href="/a">A duplicate</a>
                    <a href="/d">D</a>
                </body>
            </html>
        """.trimIndent()

        val links = htmlParserService.extractLinks(html, "https://example.com")

        assertEquals(4, links.size)
        assertEquals("https://example.com/a", links[0])
        assertEquals("https://example.com/b", links[1])
        assertEquals("https://example.com/c", links[2])
        assertEquals("https://example.com/d", links[3])
    }
}
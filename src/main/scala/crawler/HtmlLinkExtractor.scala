package crawler

import net.ruippeixotog.scalascraper.browser.{Browser, JsoupBrowser}
import net.ruippeixotog.scalascraper.dsl.DSL.Extract._
import net.ruippeixotog.scalascraper.dsl.DSL._

class HtmlLinkExtractor {
  val browser: Browser = JsoupBrowser()

  def getLinksForHtmlContent(pageHtml: String): List[String] = {
    val doc = browser.parseString(pageHtml)

    val items = doc >> elementList("a")

    items.map(_.attr("href"))
  }
}

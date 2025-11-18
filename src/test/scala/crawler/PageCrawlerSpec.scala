package crawler

import mock.MockHttpClient
import org.scalatest.OptionValues
import org.scalatest.matchers.should.Matchers
import org.scalatest.wordspec.AnyWordSpec

import scala.concurrent.ExecutionContext.Implicits.global

class PageCrawlerSpec extends AnyWordSpec with Matchers with OptionValues{

  val mockHttpClient = new MockHttpClient
  private val startPageUrl: PageUrl = PageUrl("http://somesite.com").value
  val pageCrawler = new PageCrawler(
    crawlerHttpClient = mockHttpClient, linkExtractor = new HtmlLinkExtractor,
    urlVisitStrategy = new SameDomainStrategy(startPageUrl), baseUrl = startPageUrl
  )


  "Page Crawler" when {

    "Provided a valid URL" should {
      "Successfully crawl all available pages" in {
        val allPages: List[PageSubLinks] = pageCrawler.crawl("http://somesite.com/main.html")

        allPages.map(_.pageUrl) should contain only(
          "http://somesite.com/main.html",
          "http://somesite.com/page1.html",
          "http://somesite.com/page2.html",
        )

        allPages should contain(
          PageSubLinks(
            pageUrl = "http://somesite.com/main.html",
            childLinks = List(
              "/page1.html",
              "/page2.html",
              "/page3.html"
            )
          )
        )
        allPages should contain(
          PageSubLinks(
            pageUrl = "http://somesite.com/page1.html",
            childLinks = List(
              "/page1.html"
            )
          )
        )
        allPages should contain(
          PageSubLinks(
            pageUrl = "http://somesite.com/page2.html",
            childLinks = List(
              "/main.html",
              "http://www.someothersite.com/blah.html"
            )
          )
        )
      }
    }

  }

}

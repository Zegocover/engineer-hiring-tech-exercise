package crawler

import org.scalatest.OptionValues
import org.scalatest.matchers.should.Matchers
import org.scalatest.wordspec.AnyWordSpec

class PageUrlSpec extends AnyWordSpec with Matchers with OptionValues{

  "URl Builder" can {
    val startUrl = PageUrl("http://www.example.com/some/page").value
    val urlBuilder = new UrlBuilder(startUrl)
    "Separate out default host from start url" in {
      urlBuilder.baseHost shouldBe "www.example.com"
    }
    "Retain port when non-standard" in {
      val url = "http://localhost:8080/some/page"
      val urlBuilderWithPort = new UrlBuilder(PageUrl(url).value)
      urlBuilderWithPort.baseHost shouldBe "localhost:8080"
      val builtUrl = urlBuilderWithPort.buildUrl(url).value
      builtUrl.fullUrl should endWith (":8080/some/page")
      builtUrl.url should endWith (":8080/some/page")
    }

    "Normalize a URL to its separate components" when {
      "given a valid URL including the scheme and host" should {
        val url = "http://www.example.com/here/is/a/path/page.html"
        "separate out the hostname and path" in {
          val pageUrl = urlBuilder.buildUrl(url)

          pageUrl.value.port shouldBe empty
          pageUrl.value.hostname shouldBe "www.example.com"
          pageUrl.value.path shouldBe "/here/is/a/path/page.html"
        }
        "Rebuild from PageURL representation to a full URL" in {
          val pageUrl = urlBuilder.buildUrl(url)
          pageUrl.value.fullUrl shouldBe url
        }
      }
      "given a valid URL including the scheme and host and query string" should {
        val url = "http://www.example.com/here/is/a/path/page.html?id=123&something=blah"
        "separate out the hostname and path" in {
          val pageUrl = urlBuilder.buildUrl(url)

          pageUrl.value.port shouldBe empty
          pageUrl.value.hostname shouldBe "www.example.com"
          pageUrl.value.path shouldBe "/here/is/a/path/page.html?id=123&something=blah"
        }
      }
    }
    "Build a URL and use the default hostname" when {
      "Given a relative URL" should {
        "Build the full URL with the deafult hostname" in {
          val pageUrl = urlBuilder.buildUrl("/some/relative/url/page.html")

          pageUrl.value.port shouldBe empty
          pageUrl.value.hostname shouldBe "www.example.com"
          pageUrl.value.path shouldBe "/some/relative/url/page.html"
        }
      }

    }



  }

}

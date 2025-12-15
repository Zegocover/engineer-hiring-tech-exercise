package zego.tech.exercise

import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers
import sttp.client4.UriContext
import sttp.client4.testing.{ResponseStub, SyncBackendStub}
import sttp.client4.wrappers.FollowRedirectsBackend
import sttp.model.{Header, StatusCode, Uri}

class WebCrawlerSpec extends AnyFlatSpec with Matchers {

  private val noRobotsTxtBackend = SyncBackendStub
    .whenRequestMatches(_.uri.path == Seq("robots.txt"))
    .thenRespondNotFound()

  private def pageTemplate(links: Uri*) =
    s"""<html><body>${
      links.map(link => s"""<p>Goto <a href="$link">link</a> next!</p>""").mkString("\n")
    }</body></html>"""

  it should "find all searchable URIs" in {
    val stub = noRobotsTxtBackend
      .whenRequestMatches(_.uri.path == Seq(""))
      .thenRespondExact(pageTemplate(uri"https://localhost/index.html"))
      .whenRequestMatches(req => req.uri.path == Seq("index.html"))
      .thenRespondExact(pageTemplate(uri"https://localhost/about.html"))
      .whenRequestMatches(req => req.uri.path == Seq("about.html"))
      .thenRespondOk()

    val results = new WebCrawler(backend = stub).crawl(uri"https://localhost/").toSeq

    results should contain only(
      uri"https://localhost/",
      uri"https://localhost/index.html",
      uri"https://localhost/about.html"
    )
  }

  it should "not follow urls it has already seen" in {
    val stub = noRobotsTxtBackend
      .whenRequestMatches(req => req.uri.path == Seq("index.html") || req.uri.path == Seq(""))
      .thenRespondExact(pageTemplate(uri"https://localhost/index.html", uri"https://localhost/about.html"))
      .whenRequestMatches(req => req.uri.path == Seq("about.html"))
      .thenRespondExact(pageTemplate(uri"https://localhost/index.html", uri"https://localhost/about.html"))

    val results = new WebCrawler(backend = stub).crawl(uri"https://localhost/").toSeq

    results should contain only(
      uri"https://localhost/",
      uri"https://localhost/index.html",
      uri"https://localhost/about.html",
    )
  }

  it should "gracefully handle errors" in {
    val stub = noRobotsTxtBackend
      .whenRequestMatches(_.uri.path == Seq(""))
      .thenRespondExact(pageTemplate(uri"https://localhost/index.html"), StatusCode(404))
      .whenRequestMatches(req => req.uri.path == Seq("index.html"))
      .thenRespondExact(pageTemplate(uri"https://localhost/about.html"), StatusCode(500))
      .whenRequestMatches(req => req.uri.path == Seq("about.html"))
      .thenRespondOk()

    val results = new WebCrawler(backend = stub).crawl(uri"https://localhost/").toSeq

    results should contain only(
      uri"https://localhost/",
      uri"https://localhost/index.html",
      uri"https://localhost/about.html"
    )
  }

  it should "not follow urls if previously redirected to them" in {
    val stub = noRobotsTxtBackend
      .whenRequestMatches(_.uri.path == Seq(""))
      .thenRespond(ResponseStub.exact("Moved", StatusCode.Found, Seq(Header.location("https://localhost/index.html"))))
      .whenRequestMatches(_.uri == uri"https://localhost/index.html")
      .thenRespondOk()

    val results = new WebCrawler(backend = FollowRedirectsBackend(stub)).crawl(uri"https://localhost/").toSeq

    results should contain only(
      uri"https://localhost/",
      uri"https://localhost/index.html",
    )
  }

  it should "not follow URIs forbidden by a robots.txt file" in {
    val stub = SyncBackendStub
      .whenRequestMatches(_.uri.path == Seq("robots.txt"))
      .thenRespondExact(
        """User-agent: *
          |Disallow: /about.html
          |""".stripMargin)
      .whenRequestMatches(req => req.uri.path == Seq(""))
      .thenRespondExact(pageTemplate(uri"https://localhost/about.html"))
      .whenRequestMatches(req => req.uri.path == Seq("about.html"))
      .thenRespondExact(pageTemplate(uri"/forbidden-link.html"))
      .whenRequestMatches(req => req.uri.path == Seq("forbidden-link.html"))
      .thenRespondOk()

    val results = new WebCrawler(backend = stub).crawl(uri"https://localhost/").toSeq

    results should contain only(
      uri"https://localhost/",
      uri"https://localhost/about.html",
    )
  }
}

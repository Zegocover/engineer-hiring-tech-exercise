package zego.tech.exercise

import org.scalatest.LoneElement.convertToCollectionLoneElementWrapper
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers
import sttp.client4.Response
import sttp.model.Uri.UriContext
import sttp.model.{Method, RequestMetadata}

class UriFinderSpec extends AnyFlatSpec with Matchers {

  behavior of "parsing response for URIs"

  it should "find URLs from HTML hrefs" in {
    val body =
      """<html>
        |  <body>
        |  <a href="https://localhost/index.html">link</a>
        |  <div>
        |    <a href="https://localhost/about.html">link</a>
        |  </div>
        |  </body>
        |</html>""".stripMargin

    val dummyResponse = Response.ok(body, RequestMetadata(Method.GET, uri"https://localhost/", Seq.empty))
    val result = UriFinder.parseUrlsFromHtml(dummyResponse)

    result should contain allOf(
      uri"https://localhost/index.html",
      uri"https://localhost/about.html"
    )
  }

  it should "find URLs from HTML hrefs containing relative paths" in {
    val body =
      """<html>
        |  <body>
        |  <a href="/index.html">link</a>
        |  <div>
        |    <a href="about.html">link</a>
        |  </div>
        |  </body>
        |</html>""".stripMargin

    val dummyResponse = Response.ok(body, RequestMetadata(Method.GET, uri"https://localhost/", Seq.empty))
    val result = UriFinder.parseUrlsFromHtml(dummyResponse)

    result should contain allOf(
      uri"https://localhost/index.html",
      uri"https://localhost/about.html"
    )
  }

  it should "ignore URLs pointing to domains outside of the target request" in {
    val body =
      """<html>
        |  <body>
        |  <a href="https://localhost/index.html">link</a>
        |  <div>
        |    <a href="https://www.google.com/about.html">link</a>
        |  </div>
        |  </body>
        |</html>""".stripMargin

    val dummyResponse = Response.ok(body, RequestMetadata(Method.GET, uri"https://localhost/", Seq.empty))
    val result = UriFinder.parseUrlsFromHtml(dummyResponse)

    result.loneElement shouldBe uri"https://localhost/index.html"
  }
}

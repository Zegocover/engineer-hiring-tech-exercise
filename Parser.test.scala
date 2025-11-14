import org.jsoup.Jsoup
import org.scalamock.ziotest.ScalamockZIOSpec
import zio.{Scope, ZIO, ZLayer}
import zio.test.*

import scala.runtime.stdLibPatches.Predef.assert as parser

object ParserTest extends ScalamockZIOSpec:

  private val Url = "https://example.com"

  override def spec: Spec[TestEnvironment & Scope, Any] = invlid + valid

  val invlid = suite("invalid inputs")(
    test("should ignore invalid href") {
      val doc =
        """
          |<html>
          |  <body>
          |    <a href=""/>
          |    <a href="   "/>
          |    <a href="xxx://"/>
          |  </body>
          |</html>
          |""".stripMargin

      for
        _ <- ZIO.serviceWith[HttpClient]: mock =>
          mock.get.expects(Url).returnsZIO(Jsoup.parse(doc))
        client <- ZIO.service[HttpClient]
        urls <- ParserLive("", client).parse(Url)
      yield assert(urls)(Assertion.isEmpty)
    }.provide(mock[HttpClient]),

    test("should ignore empty href") {
      val doc =
        """
          |<html>
          |  <body>
          |    <a/>
          |  </body>
          |</html>
          |""".stripMargin

      for
        _ <- ZIO.serviceWith[HttpClient]: mock =>
          mock.get.expects(Url).returnsZIO(Jsoup.parse(doc))
        client <- ZIO.service[HttpClient]
        urls <- ParserLive("", client).parse(Url)
      yield assert(urls)(Assertion.isEmpty)
    }.provide(mock[HttpClient]),

    test("should ignore href not in <a>") {
      val doc =
        """
          |<html>
          |  <body>
          |    <div href="/"/>
          |  </body>
          |</html>
          |""".stripMargin
      for
        _ <- ZIO.serviceWith[HttpClient]: mock =>
          mock.get.expects(Url).returnsZIO(Jsoup.parse(doc))
        client <- ZIO.service[HttpClient]
        urls <- ParserLive("", client).parse(Url)
      yield assert(urls)(Assertion.isEmpty)
    }.provide(mock[HttpClient])
  )

  val valid = suite("valid inputs")(
    test("should normalize urls") {
      val doc =
        """
          |<html>
          |  <body>
          |    <a href="/"/>
          |    <a href="/info"/>
          |  </body>
          |</html>
          |""".stripMargin

      for
        _ <- ZIO.serviceWith[HttpClient]: mock =>
          mock.get.expects(Url).returnsZIO(Jsoup.parse(doc, "https://example.com"))
        client <- ZIO.service[HttpClient]
        urls <- ParserLive("", client).parse(Url)

      yield assert(urls)(
        Assertion.hasSameElements(Seq("https://example.com/", "https://example.com/info"))
      )
    }.provide(mock[HttpClient]),

    test("should return absolute link to other domains") {
      val doc =
        """
          |<html>
          |  <body>
          |    <a href="https://google.com"/>
          |    <a href="https://en.wikipedia.org"/>
          |    <a href="https://example.com/ping"/>
          |  </body>
          |</html>
          |""".stripMargin

      for
        _ <- ZIO.serviceWith[HttpClient]: mock =>
          mock.get.expects(Url).returnsZIO(Jsoup.parse(doc))
        client <- ZIO.service[HttpClient]
        urls <- ParserLive("", client).parse(Url)

      yield assert(urls)(
        Assertion.hasSameElements(Seq(
          "https://google.com",
          "https://en.wikipedia.org",
          "https://example.com/ping"
        ))
      )
    }.provide(mock[HttpClient])
  )

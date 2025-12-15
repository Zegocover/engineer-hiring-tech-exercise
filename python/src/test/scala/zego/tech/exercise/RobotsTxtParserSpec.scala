package zego.tech.exercise

import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers
import sttp.client4.{Response, UriContext}
import sttp.model.{Method, RequestMetadata}

class RobotsTxtParserSpec extends AnyFlatSpec with Matchers {

  behavior of "robots.txt parsing"

  it should "parse a valid robots.txt file" in {
    val body =
      """User-agent: knownbot
        |Sitemap: https://localhost/sitemap.xml
        |
        |Disallow: /secret
        |
        |User-agent: *
        |Disallow: /
        |Disallow: /specific
        |
        |User-agent: foo
        |Disallow: /
        |""".stripMargin

    val dummyRequest = Response.ok(body, RequestMetadata(Method.GET, uri"https://localhost/", Seq.empty))
    val result = RobotsTxtParser.parseGlobalCrawlerRules(dummyRequest)
    result should contain only(uri"https://localhost/", uri"https://localhost/specific")
  }
}

import org.jsoup.Jsoup
import zio.{Scope, ZLayer}
import zio.test.*

import scala.runtime.stdLibPatches.Predef.assert as parser

object ParserTest extends ZIOSpecDefault:
  val parser = Parser()

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

      val urls = parser.parse(Jsoup.parse(doc), "")

      assert(urls)(Assertion.isEmpty)
    },

    test("should ignore empty href") {
      val doc =
        """
          |<html>
          |  <body>
          |    <a/>
          |  </body>
          |</html>
          |""".stripMargin

      val urls = parser.parse(Jsoup.parse(doc), "")

      assert(urls)(Assertion.isEmpty)
    },

    test("should ignore href not in <a>") {
      val doc =
        """
          |<html>
          |  <body>
          |    <div href="/"/>
          |  </body>
          |</html>
          |""".stripMargin

      val urls = parser.parse(Jsoup.parse(doc), "")

      assert(urls)(Assertion.isEmpty)
    }
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

      val urls = parser.parse(Jsoup.parse(doc, "https://example.com"), "https://example.com")

      assert(urls)(
        Assertion.hasSameElements(Seq("https://example.com/", "https://example.com/info"))
      )
    },

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

      val urls = parser.parse(Jsoup.parse(doc, "https://example.com"), "https://example.com")

      assert(urls)(
        Assertion.hasSameElements(Seq(
          "https://google.com",
          "https://en.wikipedia.org",
          "https://example.com/ping"
        ))
      )
    }
  )

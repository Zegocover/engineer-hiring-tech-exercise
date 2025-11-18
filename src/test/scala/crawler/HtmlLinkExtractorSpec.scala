package crawler

import org.scalatest.matchers.should.Matchers
import org.scalatest.wordspec.AnyWordSpec

class HtmlLinkExtractorSpec extends AnyWordSpec with Matchers{

  "Html Extractor" can {
    val linkExtractor = new HtmlLinkExtractor

    "Extract anchor tags from HTML content" when {

      "given HTML with valid links included" should {
        val validHtml =
          """
            |<html>
            | <head>
            |   <title>Some test stuff</title>
            | </head>
            | <body>
            |   <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit</p>
            |   <a href="/next/page">some link</a>
            |   <h2>Some other section</h2>
            |   <p>A paragraph
            |     <a href="/another/link">Another link</a>
            |   </p>
            |   <h2>Another section</h2>
            |   <div>
            |     <p>
            |       Some text<a href="/more/nested/link">A more nested link</a>
            |     </p>
            |   </div>
            |   <a href="/more/link/page1.html">More link</a>
            | </body>
            |</html>
            |
            |""".stripMargin


        "Return a full list of the relevant anchor tag href attributes" in {
          val foundLinks = linkExtractor.getLinksForHtmlContent(validHtml)
          foundLinks should have size (4)
          foundLinks should contain only (
            "/next/page",
            "/another/link",
            "/more/nested/link",
            "/more/link/page1.html"
          )
        }
      }


    }
  }


}

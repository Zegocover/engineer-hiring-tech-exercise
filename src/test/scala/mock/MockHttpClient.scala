package mock

import crawler.HttpClient
import sttp.model.Uri

import scala.concurrent.Future

class MockHttpClient extends HttpClient {

  def htmlTemplate(title: String, url: String, someLinks: String): MockPage =
    MockPage(url = "/page1.html",
      html =
        s"""
           | <html>
           |   <head>
           |     <title>$title</title>
           |   </head>
           |   <body>
           |     <p>placeholder text</p>
           |     $someLinks
           |   </body>
           | </html>
           |
           |""".stripMargin
    )

  val main: MockPage = htmlTemplate("Main Page",
    "/main.html",
    """
      | <a href="/page1.html">Page 1 link</a>
      | <a href="/page2.html">Page 2 link</a>
      | <a href="/page3.html">Page 3 link</a>
      |""".stripMargin)

  val page1: MockPage = htmlTemplate("Page 1",
    "/page1.html",
    """
      | <a href="/page1.html">Page 1 link</a>
      |""".stripMargin)
  val page2: MockPage = htmlTemplate("Page 2",
    "/page2.html",
    """
      | <a href="/main.html">Page 1 link</a>
      | <a href="http://www.someothersite.com/blah.html">Page 1 link</a>
      |""".stripMargin)


  override def loadUrl(url: Uri): Future[Option[String]] = url.pathToString match {
    case p if p.endsWith("main.html") => pageFuture(main)
    case p if p.endsWith("page1.html") => pageFuture(page1)
    case p if p.endsWith("page2.html") => pageFuture(page2)
    case _ => Future.successful(None)
  }

  private def pageFuture(page: MockPage): Future[Some[String]] = {
    Future.successful(Some(page.html))
  }
}

case class MockPage(url: String, html: String)

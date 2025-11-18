package app

import crawler._

import scala.concurrent.ExecutionContext.Implicits.global

class CrawlerApp(startUrl: PageUrl)  {
  val pageCrawler = new PageCrawler(
    crawlerHttpClient = new CrawlerHttpClient(),
    linkExtractor = new HtmlLinkExtractor,
    urlVisitStrategy = new SameDomainStrategy(startUrl),
    baseUrl = startUrl
  )

  def start(): Unit = {
    pageCrawler.crawl(startUrl.fullUrl)
  }
}

object CrawlerApp {

  val usage: String =
    """
      | Provide a single argument with the baseURL to crawl.
      | Usage: <crawler app> http://<domain>/exampleStartPage.html
      |""".stripMargin

  def main(args: Array[String]): Unit = {
    if (args.length != 1) {
      println(usage)
    } else {
      PageUrl(args.head).fold(
        println("Invalid argument")
      )(url => {
        val app = new CrawlerApp(url)
        app.start()
      })
    }
  }
}



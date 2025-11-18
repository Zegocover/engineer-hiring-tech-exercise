package crawler

import cats.syntax.all._
import sttp.model.Uri

import scala.annotation.tailrec
import scala.collection.concurrent.TrieMap
import scala.collection.mutable
import scala.concurrent.duration.DurationInt
import scala.concurrent.{Await, ExecutionContext, Future}
import scala.language.postfixOps

class PageCrawler(
                   crawlerHttpClient: HttpClient,
                   linkExtractor: HtmlLinkExtractor,
                   urlVisitStrategy: UrlVisitStrategy,
                   baseUrl: PageUrl)
                 (
                   implicit ec: ExecutionContext
                 ) {

  val urlBuilder: UrlBuilder = new UrlBuilder(baseUrl)

  private val visitedUrls: mutable.Map[String, Boolean] = TrieMap()

  private case class RecursionState(accumulatedLinks: List[PageSubLinks], shouldRecurse: Boolean)

  def crawl(startUrl: String): List[PageSubLinks] = {
    traverseLevels(List(startUrl), Nil)
  }

  @tailrec
  private def traverseLevels(nextUrls: List[String], accumulatedLinks: List[PageSubLinks], level: Int = 1): List[PageSubLinks] = {
    val nextLevel: Future[List[PageSubLinks]] = getPageLinksWithInfo(nextUrls)
    val nextLinks: List[PageSubLinks] = Await.result(nextLevel, 5 seconds)

    val recursionState = nextLinks match {
      case Nil => RecursionState(accumulatedLinks, shouldRecurse = false)
      case childLinks =>  RecursionState(accumulatedLinks ++ childLinks, shouldRecurse = true)
    }
    if (!recursionState.shouldRecurse) {
      recursionState.accumulatedLinks
    } else {
      traverseLevels(nextLinks.flatMap(_.childLinks), recursionState.accumulatedLinks, level + 1)
    }
  }

  private def loadUrlsForPage(url: String): Future[Option[PageSubLinks]] = {
    (for {
      builtUrl <- urlBuilder.buildUrl(url)
      urlString = builtUrl.fullUrl
      _ = builtUrl if !visitedUrls.contains(urlString) && urlVisitStrategy.isForTraverse(builtUrl)
      _ = visitedUrls.put(urlString, true)
      loadUri <- Uri.parse(urlString).toOption
    } yield {
      crawlerHttpClient.loadUrl(loadUri)
    }.map {
      // distinguish between page loads/exists and not
      case Some(responseHtml) => Some(
        PageSubLinks(builtUrl.fullUrl, linkExtractor.getLinksForHtmlContent(responseHtml))
      )
      case None => None
    }).sequence.map(_.flatten)
  }

  private def getPageLinksWithInfo(nextLevelUrls: List[String]): Future[List[PageSubLinks]] = {
    // fetch all pages in the current level, as 1 future
    nextLevelUrls.map(loadUrlsForPage).sequence
      .map(_.flatten)
      .map{pageList =>
        for (page <- pageList) yield {
          page.displayInfo()
          page
        }
      }
  }

}

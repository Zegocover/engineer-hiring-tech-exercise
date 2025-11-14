import org.jsoup.Jsoup
import zio.stream.*
import zio.{Console, Queue, ZIO}

import scala.util.Try
import scala.collection.concurrent
import java.net.URL

// TODO: extract as config
class Crawler(domain: String, numThreads: Int):
  private val visitedUrls = concurrent.TrieMap.empty[String, Boolean]

  def crawl(startUrl: String): ZIO[Any, Throwable, Unit] = for
    _ <- ZIO.logInfo(s"starting crawling for domain: $domain")
    // _ <- task(startUrl)
    _ <- task(startUrl)
    _ <- ZIO.logInfo(s"finish crawling for domain: $domain")
  yield ()

  private def task(url: String): ZIO[Any, Nothing, Any] =
    val processed = visitedUrls.getOrElseUpdate(url, false)
    if processed
    then ZIO.unit
    else task0(url).ignore

  private def task0(url: String): ZIO[Any, Throwable, Seq[String]] = for
    /* TODO: make fetching html more configurable: rate limiter, retry, follow redirects
        use another library, e.g. sttp-client, zio-http */
    doc <- ZIO.attemptBlocking(Jsoup.connect(url).get())
    urls <- ZIO.attempt(Parser().parse(doc, domain))

    _ <- ZIO.attempt(visitedUrls.put(url, true))

    filteredUrls = urls.filter(checkDomain)
      .filterNot(visitedUrls.isDefinedAt)
    _ <- printResult(url, urls)

    _ <- ZIO.foreachPar(filteredUrls)(task)
  yield filteredUrls

  private def printResult(base: String, urls: Seq[String], onlyDomain: Boolean = true) = {
    val pred =
      if onlyDomain
      then checkDomain
      else (_: String) => true

    Console.printLine(
      s"""base url: $base
         |urls on the page: ${urls.view.filter(pred).mkString("\n ")}
         |""".stripMargin)
  }

  private def checkDomain(url: String) =
    Try(URL(url).getHost == domain).getOrElse(false)

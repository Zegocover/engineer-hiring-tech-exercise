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
    _ <- loop(Seq(startUrl))
    _ <- ZIO.logInfo(s"finish crawling for domain: $domain")
  yield ()

  private def loop(url: Seq[String]): ZIO[Any, Throwable, Unit] =
    ZStream.fromIterable(url)
      .flatMapPar(numThreads): url =>
        // TODO: Add logging for errors
        ZStream.fromIterableZIO(worker(url).orElseSucceed(Seq.empty[String]))
      .runCollect
      .flatMap(loop)

  private def worker(url: String) = for
    /* TODO: make fetching html more configurable: rate limiter, retry, follow redirects
        use another library, e.g. sttp-client, zio-http */
    _ <- ZIO.attempt(visitedUrls.put(url, true))

    doc <- ZIO.attemptBlocking(Jsoup.connect(url).get())
    urls <- ZIO.attempt(Parser().parse(doc, domain))

    filteredUrls = urls.filter(checkDomain)
      .filterNot(visitedUrls.isDefinedAt)
    _ <- printResult(url, urls)
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

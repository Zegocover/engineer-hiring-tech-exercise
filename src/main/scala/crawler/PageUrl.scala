package crawler

import java.net.URL
import scala.util.Try

case class PageUrl(
                  hostname: String,
                  path: String,
                  scheme: String,
                  port: Option[Int]
                  ) {

  def fullUrl: String = s"$scheme$hostname${port.map(p => s":$p").getOrElse("")}$path"

  def url: String = s"$hostWithPort$path"

  def hostWithPort: String = s"$hostname${port.map(p => s":$p").getOrElse("")}"
}

object PageUrl {

  /**
   * Construct with raw URL including scheme
   */
  def apply(rawUrl: String): Option[PageUrl] = {
    Try {
      new URL(rawUrl)
    }.map{ jUrl =>
      val query = if (jUrl.getQuery != null && jUrl.getQuery.nonEmpty) "?".concat(jUrl.getQuery) else ""
      PageUrl(
        hostname = jUrl.getHost,
        path = s"${jUrl.getPath}${query}",
        scheme = jUrl.getProtocol + "://",
        port =
          if (jUrl.getPort != 80 && jUrl.getPort > 0) {
            Some(jUrl.getPort)
          } else {
            None
          }
      )
    }.toOption
  }

  def apply(baseHost: String, path: String): Option[PageUrl] = {
    Try {
      new URL(baseHost + "/" + path) // try to construct to confirm its valid
    }.toOption.flatMap{_ =>
      PageUrl(baseHost + path)
    }
  }

}

class UrlBuilder(startUrl: PageUrl) {

  val baseHost: String = startUrl.hostWithPort
  val baseUrl: String = startUrl.scheme + baseHost

  def buildUrl(rawUrl: String): Option[PageUrl] = {
    PageUrl(rawUrl) match {
      case url@Some(_) => url
      case None =>  PageUrl(baseUrl, rawUrl) // try to construct from default host
    }
  }
}

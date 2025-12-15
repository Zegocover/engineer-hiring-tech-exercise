package zego.tech.exercise

import sttp.client4.Response
import sttp.model.Uri

object RobotsTxtParser {
  /** A rough robots.txt parser to figure out if the target domain allows crawlers.
   *
   * @param robotsTxt raw robots.txt contents
   * @return the urls they do not want crawled
   */
  def parseGlobalCrawlerRules(robotsTxt: Response[String]): Set[Uri] = {
    if (!robotsTxt.isSuccess) Set.empty[Uri]
    else {
      val group = robotsTxt.body.split("\n").dropWhile(_ != "User-agent: *")

      if (group.isEmpty) Set.empty[Uri]
      else
        group.tail
          .takeWhile(!_.startsWith("User-agent:"))
          .flatMap(parseDisallowRule)
          .map(robotsTxt.request.uri.withWholePath(_))
          .toSet
    }
  }

  private def parseDisallowRule(raw: String) =
    "^Disallow: (.+)$".r
      .findFirstMatchIn(raw)
      .map(_.group(1))
}

package zego.tech.exercise

import ch.digitalfondue.jfiveparse.{Element, JFiveParse, Selector}
import sttp.client4.Response
import sttp.model.Uri

import scala.jdk.CollectionConverters.CollectionHasAsScala

object UriFinder {

  /** Find links in a page by optimistically assuming an HTML payload and searching all elements for any href
   * attributes. This will expand any relative paths to full URIs based on the URI in the initial request. It also
   * ignores URIs which do not belong to the original request domain.
   *
   * @param response the full HTTP response
   * @return a list of discovered URIs
   */
  def parseUrlsFromHtml(response: Response[String]): Set[Uri] =
    findAllHrefs(response)
      .filter(targetDomainOnly(_, response.request.uri))
      .map(expandPathToUri(_, response.request.uri))

  private def findAllHrefs(response: Response[String]): Set[Uri] = {
    try {
      JFiveParse.parse(response.body)
        .getAllNodesMatching[Element](Selector.select().attr("href").toMatcher).asScala
        .map(_.getAttribute("href"))
        .flatMap(Uri.parse(_).toOption)
        .toSet
    } catch {
      // Ignore HTML errors and consider the page searched
      case err: Throwable =>
        sys.error(err.getMessage)
        Set.empty
    }
  }

  /** If a URI consists of only a path then we need to fill in the host for the full URI.
   *
   * @param uri    a potentially partially formed uri
   * @param domain the default uri details to use
   * @return a complete uri
   */
  private def expandPathToUri(uri: Uri, domain: Uri): Uri =
    if (uri.isAbsolute) uri
    else
      domain.copy(
          scheme = uri.scheme.orElse(domain.scheme),
          authority = uri.authority.orElse(domain.authority),
          fragmentSegment = uri.fragmentSegment.orElse(domain.fragmentSegment)
        )
        .withWholePath(uri.pathToString)

  private def targetDomainOnly(uri: Uri, domain: Uri): Boolean =
    uri.isRelative || uri.host == domain.host
}

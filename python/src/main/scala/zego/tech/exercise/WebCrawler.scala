package zego.tech.exercise

import sttp.client4.*
import sttp.model.{HeaderNames, Uri}

import scala.collection.immutable.Queue

/** A simple, synchronous web crawler. Obeys robots.txt if the target domain provides one. Optimistically assumes most
 * pages will return HTML and ignores their contents if they don't. If the site redirects the crawler it will make a
 * note of the links encountered during the redirect and emit them too.
 *
 * @param backend the HTTP client to execute requests with
 */
class WebCrawler(backend: SyncBackend) {

  private case class State(requestQueue: Queue[Uri], searchedUris: Set[Uri])

  def crawl(domain: Uri): Iterator[Uri] = {
    val robotsTxtResponse = basicRequest.get(domain.withWholePath("robots.txt")).response(asStringAlways).send(backend)
    val disallowedUris = RobotsTxtParser.parseGlobalCrawlerRules(robotsTxtResponse)

    val startingPoint = State(requestQueue = Queue(domain), searchedUris = Set.empty)

    // Stateful iterator, where each step returns a pair of (<URIs encountered> -> <Crawling state>). Slightly more
    // involved than a normal iterator since each step can return 0 or more discovered URIs (that we then need to emit from
    // our iterator).
    Iterator.unfold(startingPoint) { state =>
        state.requestQueue
          .dequeueOption
          .map {
            // Skip a URI we've seen before and don't report it.
            case (uri, remainingRequests) if state.searchedUris.contains(uri) =>
              Set.empty[Uri] -> state.copy(requestQueue = remainingRequests)

            // Check if the URI was disallowed by robots.txt, and if so we should report but otherwise ignore it.
            case (uri, remainingRequests) if disallowedUris.contains(uri) =>
              Set(uri) -> state.copy(requestQueue = remainingRequests)

            // Core crawler logic, execute a GET request assuming it might return a HTML doc, after which we scan it for
            // links.
            case (uri, remainingRequests) =>
              val response = basicRequest.get(uri)
                .response(asStringAlways)
                .send(backend)

              val newUris = UriFinder.parseUrlsFromHtml(response)

              // check if a URL we searched actually redirected to another URL,
              // in which case we need to mark the real URL as searched
              val redirects = response.history.flatMap(_.header(HeaderNames.Location)).map(Uri.unsafeParse).toSet

              val searchedUris = redirects + uri
              val searchableUris = remainingRequests ++ newUris

              searchedUris -> State(searchableUris, state.searchedUris ++ searchedUris)
          }
      }
      .flatten
  }
}

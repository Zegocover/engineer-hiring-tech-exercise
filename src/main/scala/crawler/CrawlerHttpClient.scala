package crawler


import sttp.client4.Backend
import sttp.model.Uri

import scala.concurrent.{ExecutionContext, Future}

class CrawlerHttpClient(implicit ec: ExecutionContext) extends HttpClient {

  import sttp.client4.httpclient.HttpClientFutureBackend
  implicit val backend: Backend[Future] = HttpClientFutureBackend()


  def loadUrl(url: Uri): Future[Option[String]] = {

    sttp.client4.quickRequest.get(url).send(backend)
      .map {
        case resp if resp.isSuccess => Some(resp.body)
        case errResp =>
          println(s"Failed loading: response code: ${errResp.code} for: $url ")
          None
      }
  }

}

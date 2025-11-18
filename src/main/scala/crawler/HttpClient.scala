package crawler

import sttp.model.Uri

import scala.concurrent.Future

trait HttpClient {

  def loadUrl(url: Uri): Future[Option[String]]
}

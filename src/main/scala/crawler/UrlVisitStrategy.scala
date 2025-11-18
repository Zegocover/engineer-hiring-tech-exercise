package crawler

trait UrlVisitStrategy {
  def isForTraverse(pageUrl: PageUrl): Boolean
}

class SameDomainStrategy(startUrl: PageUrl) extends UrlVisitStrategy {

  val baseHost: String = startUrl.hostWithPort

  override def isForTraverse(pageUrl: PageUrl): Boolean =
    pageUrl.hostWithPort == baseHost
}

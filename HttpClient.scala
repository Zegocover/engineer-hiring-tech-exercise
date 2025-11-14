import org.jsoup.Jsoup
import org.jsoup.nodes.Document
import zio.ZIO

trait HttpClient:
  // TODO: move parsing Document into Parser
  // def get(url: String): ZIO[Any, Throwable, String]
  def get(url: String): ZIO[Any, Throwable, Document]
  
object HttpClient:
  // TODO: make it ZLayer to support DI
  val Default: HttpClient = url => ZIO.attemptBlocking(Jsoup.connect(url).get())

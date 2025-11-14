import org.jsoup.nodes.Document
import zio.Task

import java.net.URL
import scala.util.Try

trait Parser:
  def parse(url: String): Task[Seq[String]]

class ParserLive(domain: String, client: HttpClient) extends Parser: // TODO: add optional config
  def parse(url: String): Task[Seq[String]] =
    val urls = Seq.newBuilder[String]

    for 
      doc <- client.get(url)
      _ = doc.traverse: (node, _) =>
        // TODO: check all possible elements with href
        if (node.hasAttr("href") && node.nameIs("a")) {
          urls ++= Try(node.attr("abs:href"))
            .map(new URL(_))
            .map(_.toString)
            .toOption
        }
    yield urls.result()

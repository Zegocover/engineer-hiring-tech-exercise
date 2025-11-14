import org.jsoup.nodes.Document

import java.net.URL
import scala.util.Try

class Parser: // TODO: add optional config
  def parse(doc: Document, domain: String): Seq[String] =
    val urls = Seq.newBuilder[String]

    doc.traverse: (node, _) =>
      // TODO: check all possible elements with href
      if (node.hasAttr("href") && node.nameIs("a")) {
        urls ++= Try(node.attr("abs:href"))
          .map(new URL(_))
          .map(_.toString)
          .toOption
      }

    urls.result()

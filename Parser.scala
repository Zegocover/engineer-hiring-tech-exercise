import org.jsoup.nodes.Document

class Parser: // TODO: add optional config
  def parse(doc: Document, domain: String): Seq[String] =
    val urls = Seq.newBuilder[String]

    doc.traverse: (node, _) =>
      // TODO: check all possible elements with href
      if node.hasAttr("href") && node.nameIs("a")
        then urls += node.attr("abs:href")

    urls.result()

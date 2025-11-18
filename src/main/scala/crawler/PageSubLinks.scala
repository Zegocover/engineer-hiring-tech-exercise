package crawler

case class PageSubLinks(
                         pageUrl: String,
                         childLinks: List[String]
                       ) {

  def displayInfo(): Unit = {
    val childList = childLinks.map( child => s"      |--  $child").mkString("\n")
    println(s" URL: ${pageUrl}")
    println(childList + "\n")
  }
}

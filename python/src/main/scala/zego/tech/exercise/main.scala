package zego.tech.exercise

import sttp.client4.DefaultSyncBackend
import sttp.model.Uri

import scala.util.CommandLineParser

given CommandLineParser.FromString[Uri] with
  def fromString(s: String): Uri = Uri.unsafeParse(s)

@main
def crawler(baseUrl: Uri): Unit = {
  new WebCrawler(DefaultSyncBackend()).crawl(baseUrl).foreach(println)
}

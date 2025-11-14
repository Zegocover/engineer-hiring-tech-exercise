import zio.{Scope, ZIO, ZIOAppDefault, ZIOAppArgs}

import java.net.URL

object Main extends ZIOAppDefault:
  override def run: ZIO[ZIOAppArgs & Scope, Any, Any] = for
    args <- ZIOAppArgs.getArgs
    startUrl <- if args.length < 1
                then ZIO.dieMessage("url was not provided")
                else ZIO.succeed(args(0))
    domain <- ZIO.attempt(URL(startUrl).getHost)
    _ <- Crawler(domain, 4, ParserLive(domain, HttpClient.Default)).crawl(startUrl)
  yield ()
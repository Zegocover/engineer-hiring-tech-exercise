import org.scalamock.ziotest.ScalamockZIOSpec
import zio.*
import zio.test.*

object CrawlerSpec extends ScalamockZIOSpec:
  override def spec: Spec[TestEnvironment & Scope, Any] = basic

  val basic = suite("Crawler")(
    test("should ignore single exception during parsing") {
      for
        _ <- ZIO.serviceWith[Parser]: mock =>
          mock.parse.expects("https://example.com")
            .failsZIO(new IllegalArgumentException("failed to parse html document"))
            .once()
        parser <- ZIO.service[Parser]
        exit <- Crawler("example.com", 1, parser).crawl("https://example.com").exit
      yield assert(exit)(Assertion.succeeds(Assertion.anything))
    }.provide(mock[Parser]) @@ TestAspect.silent,

    test("should ignore single exception during parsing in chain") {
      for
        _ <- ZIO.serviceWith[Parser]: mock =>
          mock.parse.expects("https://example.com")
            .returnsZIO(Seq("https://example.com/a", "https://example.com/b"))
            .once()
          mock.parse.expects("https://example.com/a")
            .failsZIO(new IllegalArgumentException("failed to parse html document"))
            .once()
          mock.parse.expects("https://example.com/b")
            .returnsZIO(Seq.empty)
            .once()

        parser <- ZIO.service[Parser]
        exit <- Crawler("example.com", 1, parser).crawl("https://example.com").exit
        consoleOutput <- TestConsole.output
      yield assert(exit)(Assertion.succeeds(Assertion.anything)) &&
        assert(consoleOutput)(
          Assertion.hasSize(Assertion.equalTo(2)) &&
            !Assertion.exists(Assertion.containsString("base url: https://example.com/a"))
          )
    }.provide(mock[Parser]) @@ TestAspect.silent,

    test("should visit only same domain") {
      for
        _ <- ZIO.serviceWith[Parser]: mock =>
          mock.parse.expects("https://example.com")
            .returnsZIO(Seq("https://example.com/a", "https://en.example.com/b", "https://wiki.org"))
            .once()
          mock.parse.expects("https://example.com/a")
            .returnsZIO(Seq.empty)
            .once()
          mock.parse.expects("https://en.example.com/b")
            .returnsZIO(Seq.empty)
            .never()
          mock.parse.expects("https://wiki.org")
            .returnsZIO(Seq.empty)
            .never()

        parser <- ZIO.service[Parser]
        exit <- Crawler("example.com", 1, parser).crawl("https://example.com").exit
        consoleOutput <- TestConsole.output
      yield assert(exit)(Assertion.succeeds(Assertion.anything)) &&
        assert(consoleOutput)(
          Assertion.hasSize(Assertion.equalTo(2))  &&
            Assertion.exists(Assertion.containsString("base url: https://example.com/a")) &&
            Assertion.exists(Assertion.containsString("base url: https://example.com"))
        )
    }.provide(mock[Parser]) @@ TestAspect.silent
  )
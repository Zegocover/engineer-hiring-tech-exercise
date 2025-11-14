import org.scalamock.ziotest.ScalamockZIOSpec
import zio.*
import zio.test.*

object CrawlerSpec extends ScalamockZIOSpec:
  override def spec: Spec[TestEnvironment & Scope, Any] = basic

  val basic = suite("")(
    test("should ignore single exception during parsing") {
      for
        _ <- ZIO.serviceWith[Parser]: mock =>
          mock.parse.expects("https://example.com")
            .failsZIO(new IllegalArgumentException("failed to parse html document"))
            .once()
        parser <- ZIO.service[Parser]
        exit <- Crawler("example.com", 1, parser).crawl("https://example.com").exit
      yield assert(exit)(Assertion.succeeds(Assertion.anything))
    }.provide(mock[Parser], TestConsole.silent),

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
            !Assertion.contains("base url: https://example.com/a")
          )
    }.provide(mock[Parser], TestConsole.silent)
  )
using AwesomeAssertions;

using CrawlerApp.Services;

using Microsoft.Extensions.Caching.Memory;
using Microsoft.Extensions.Logging;

using NSubstitute;

namespace Tests.Services;

public class CrawlerServiceTests
{
    private readonly IMemoryCache _cache;
    private readonly IUriContentService _mockContentService;
    private readonly CrawlerService _sut;

    public CrawlerServiceTests()
    {
        _cache = new MemoryCache(new MemoryCacheOptions());
        _mockContentService = Substitute.For<IUriContentService>();
        var mockLogger = Substitute.For<ILogger<CrawlerService>>();
        _sut = new CrawlerService(_mockContentService, _cache, mockLogger);
    }


    [Fact]
    public async Task Crawl_WithSingleUri_CrawlsUriWithExpectedResults()
    {
        // Arrange
        var uri = new Uri("https://example.com");
        var htmlContent = File.ReadAllText("data/basic-pages.html");

        // Setup mock to return HTML content - ensure non-null return
        _mockContentService
            .GetHtmlContent(uri, CancellationToken.None)
            .Returns(Task.FromResult<string?>(htmlContent));

        // Act
        await _sut.Crawl(uri, CancellationToken.None);

        // Assert
        var cachedValue = _cache.TryGetValue(uri.AbsoluteUri, out _);
        cachedValue.Should().BeTrue();

        // Verify content service was called with the initial URI
        await _mockContentService.Received(1)
            .GetHtmlContent(uri, CancellationToken.None);
    }

    [Fact]
    public async Task Crawl_WhenUriAlreadyCrawled_SkipsDuplicate()
    {
        // Arrange
        var uri = new Uri("https://example.com");

        // Pre-populate cache to indicate URI was already visited
        _cache.Set(uri.AbsoluteUri, true);

        // Act
        await _sut.Crawl(uri, CancellationToken.None);

        // Assert
        // Verify content service was NOT called since URI was already visited
        await _mockContentService.DidNotReceive()
            .GetHtmlContent(Arg.Any<Uri>(), CancellationToken.None);
    }

    [Fact]
    public async Task Crawl_WebsiteWithSubDomainUris_IgnoresSubdomains()
    {
        // Arrange
        var uri = new Uri("https://example.com");
        var htmlContent = await File.ReadAllTextAsync("data/subdomain-links.html");

        // Setup mock to return HTML content
        _mockContentService
            .GetHtmlContent(uri, CancellationToken.None)
            .Returns(Task.FromResult<string?>(htmlContent));

        // Setup mock to return empty content for any other calls (shouldn't happen)
        _mockContentService
            .GetHtmlContent(Arg.Any<Uri>(), CancellationToken.None)
            .Returns(Task.FromResult<string?>(""));

        // Act
        await _sut.Crawl(uri, CancellationToken.None);

        // Assert
        // Verify content service was called only for the initial URI (subdomain links are ignored due to host mismatch)
        await _mockContentService.Received(1)
            .GetHtmlContent(uri, CancellationToken.None);

        // Verify subdomain link was not crawled
        await _mockContentService.DidNotReceive()
            .GetHtmlContent(new Uri("https://subdomain.example.com/page2"), CancellationToken.None);
    }
    
    [Fact]
    public async Task Crawl_WebsiteWithExternalDomains_IgnoresExternalDomains()
    {
        // Arrange
        var uri = new Uri("https://example.com");
        var htmlContent = File.ReadAllText("data/external-links.html");

        // Setup mock to return HTML content for initial URI
        _mockContentService
            .GetHtmlContent(uri, CancellationToken.None)
            .Returns(Task.FromResult<string?>(htmlContent));

        // Setup mock to return empty content for any other calls (shouldn't happen)
        _mockContentService
            .GetHtmlContent(Arg.Any<Uri>(), CancellationToken.None)
            .Returns(Task.FromResult<string?>(""));

        // Act
        await _sut.Crawl(uri, CancellationToken.None);

        // Assert
        // Verify content service was called only for the initial URI
        await _mockContentService.Received(1)
            .GetHtmlContent(uri, CancellationToken.None);

        // Verify external domains were not crawled
        await _mockContentService.DidNotReceive()
            .GetHtmlContent(new Uri("https://external.com/page"), CancellationToken.None);

        await _mockContentService.DidNotReceive()
            .GetHtmlContent(new Uri("https://another-external.org/page"), CancellationToken.None);
    }
}
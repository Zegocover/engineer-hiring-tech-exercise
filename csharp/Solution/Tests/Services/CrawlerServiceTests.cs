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

    public CrawlerServiceTests(IUriContentService mockContentService, CrawlerService sut)
    {
        // Use a real IMemoryCache for integration testing since it's hard to mock properly
        _cache = new MemoryCache(new MemoryCacheOptions());
        _mockContentService = Substitute.For<IUriContentService>();
        ILogger<CrawlerService> mockLogger = Substitute.For<ILogger<CrawlerService>>();
        _sut = new CrawlerService(_mockContentService, _cache, mockLogger);
    }

    public CrawlerServiceTests(IMemoryCache cache, IUriContentService mockContentService, CrawlerService sut)
    {
        _cache = cache;
        _mockContentService = mockContentService;
        _sut = sut;
    }

    [Fact]
    public async Task Crawl_WithSingleUri_CrawlsUriWithExpectedResults()
    {
        // Arrange
        var uri = new Uri("https://example.com");
        var htmlContent = """
            <html>
                <body>
                    <a href="/page1">Link 1</a>
                    <a href="/page2">Link 2</a>
                </body>
            </html>
            """;

        // Setup mock to return HTML content - ensure non-null return
        _mockContentService
            .GetHtmlContent(uri, CancellationToken.None)
            .Returns(Task.FromResult((string?)htmlContent)!);

        // Act
        await _sut.Crawl(uri, CancellationToken.None);

        // Assert
        // Verify the URI was cached - if it was, TryGetValue should return true
        var cachedValue = _cache.TryGetValue(uri.AbsoluteUri, out _);
        Assert.True(cachedValue, "URI should have been cached after crawling");
        
        // Verify content service was called with the initial URI
        await _mockContentService.Received(1)
            .GetHtmlContent(uri, CancellationToken.None);
    }

    [Fact]
    public async Task Crawl_WhenUriAlreadyCrawled_SkipsDuplicateCrawl()
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
}
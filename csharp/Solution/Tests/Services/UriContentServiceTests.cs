using System.Net;
using System.Net.Http.Headers;

using AwesomeAssertions;

using CrawlerApp.Services;

using Microsoft.Extensions.Logging;

using NSubstitute;

namespace Tests.Services;

public class UriContentServiceTests
{
    private readonly HttpClient _mockHttpClient = Substitute.For<HttpClient>();
    private readonly ILogger<UriContentService> _mockLogger = Substitute.For<ILogger<UriContentService>>();
    private readonly UriContentService _sut;

    public UriContentServiceTests()
    {
        _sut = new UriContentService(_mockHttpClient, _mockLogger);
    }

    [Fact]
    public async Task GetContent_WithInvalidHtml_ReturnsNull()
    {
        // Arrange
        var uri = new Uri("https://example.com");

        var response = new HttpResponseMessage(HttpStatusCode.OK)
        {
            Content = new StringContent("{\"error\": \"not html\"}")
        };
        response.Content.Headers.ContentType = new MediaTypeHeaderValue("application/json");

        _mockHttpClient
            .SendAsync(Arg.Any<HttpRequestMessage>(), Arg.Any<CancellationToken>())
            .Returns(Task.FromResult(response));

        // Act
        var result = await _sut.GetHtmlContent(uri, CancellationToken.None);

        // Assert
        result.Should().BeNull();
        _mockLogger.Received().Log(
            LogLevel.Error,
            Arg.Any<EventId>(),
            Arg.Is<object>(v => v.ToString()!.Contains("Content is not html")),
            Arg.Any<Exception>(),
            Arg.Any<Func<object, Exception?, string>>());
    }

    [Fact]
    public async Task GetContent_IfHttpCallNotSuccessful_ReturnsNull()
    {
        // Arrange
        var uri = new Uri("https://example.com");

        // Create a response with failure status code
        var response = new HttpResponseMessage(HttpStatusCode.NotFound);

        _mockHttpClient
            .SendAsync(Arg.Any<HttpRequestMessage>(), Arg.Any<CancellationToken>())
            .Returns(Task.FromResult(response));

        // Act
        var result = await _sut.GetHtmlContent(uri, CancellationToken.None);

        // Assert
        result.Should().BeNull();
        _mockLogger.Received().Log(
            LogLevel.Error,
            Arg.Any<EventId>(),
            Arg.Is<object>(v => v.ToString()!.Contains("Failed to retrieve content")),
            Arg.Any<Exception>(),
            Arg.Any<Func<object, Exception?, string>>());
    }

    [Fact]
    public async Task GetContent_WithValidHtml_ReturnsContent()
    {
        // Arrange
        var uri = new Uri("https://example.com");
        var htmlContent = File.ReadAllText("data/valid-html.html");

        // Create a response with valid HTML content
        var response = new HttpResponseMessage(HttpStatusCode.OK)
        {
            Content = new StringContent(htmlContent)
        };
        response.Content.Headers.ContentType = new MediaTypeHeaderValue("text/html");

        _mockHttpClient
            .SendAsync(Arg.Any<HttpRequestMessage>(), Arg.Any<CancellationToken>())
            .Returns(Task.FromResult(response));

        // Act
        var result = await _sut.GetHtmlContent(uri, CancellationToken.None);

        // Assert
        result.Should().NotBeNull();
        result.Should().Be(htmlContent);
        result.Should().Contain("<html>");
        result.Should().Contain("Valid HTML Page");
    }
}
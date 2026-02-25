using System.Collections.Concurrent;
using HtmlAgilityPack;
using Microsoft.Extensions.Caching.Memory;
using Microsoft.Extensions.Logging;

namespace CrawlerApp.Services;

public partial class CrawlerService(IUriContentService uriContentService, IMemoryCache visitedUris, ILogger<CrawlerService> logger) : ICrawlerService
{
    public async Task Crawl(Uri initialUri, CancellationToken cancellationToken)
    {
        
        if (visitedUris.TryGetValue(initialUri.AbsoluteUri, out _))
        {
            LogAlreadyVisitedUri(logger, initialUri.AbsoluteUri);
            return;
        }

        visitedUris.Set(initialUri.AbsoluteUri, true);

        var queue = new ConcurrentQueue<Uri>();
        queue.Enqueue(initialUri);
        while (queue.TryDequeue(out var currentUri))
        {
            LogProcessingUri(logger, currentUri.AbsoluteUri);
            var content = await uriContentService.GetHtmlContent(currentUri, cancellationToken);
            if (string.IsNullOrWhiteSpace(content))
            {
                continue;
            }

            var links = ExtractLinksFromHtml(content, currentUri);
            foreach (var link in links)
            {
                if (Uri.TryCreate(link, UriKind.Absolute, out var fullUrl) &&
                    fullUrl.Host == currentUri.Host)
                {
                    if (visitedUris.TryGetValue(fullUrl.AbsoluteUri, out _))
                    {
                        LogAlreadyVisitedUri(logger, fullUrl.AbsoluteUri);
                        continue;
                    }

                    visitedUris.Set(fullUrl.AbsoluteUri, true);
                    LogAddingUri(logger, fullUrl.AbsoluteUri);
                    queue.Enqueue(fullUrl);
                    
                }
            }
        }
    }

    private static HashSet<string> ExtractLinksFromHtml(string htmlContent, Uri baseUri)
    {
        var links = new List<string>();
        var htmlDoc = new HtmlDocument();
        htmlDoc.LoadHtml(htmlContent);

        var anchorTags = htmlDoc.DocumentNode.SelectNodes("//a[@href]");
        foreach (var tag in anchorTags)
        {
            var hrefValue = tag.GetAttributeValue(name:"href", def:"");
            if (string.IsNullOrWhiteSpace(hrefValue))
            {
                continue;
            }
            var fullUrl = new Uri(baseUri, hrefValue);
            links.Add(fullUrl.ToString());
        }

        return links.ToHashSet();
    }

    [LoggerMessage(LogLevel.Information, "already visited {uri}")]
    static partial void LogAlreadyVisitedUri(ILogger<CrawlerService> logger, string uri);

    [LoggerMessage(LogLevel.Information, "adding {uri}")]
    static partial void LogAddingUri(ILogger<CrawlerService> logger, string uri);

    [LoggerMessage(LogLevel.Information, "processing {uri}")]
    static partial void LogProcessingUri(ILogger<CrawlerService> logger, string uri);
}

public interface ICrawlerService
{
    /// <summary>
    /// Crawl a given uri
    /// </summary>
    /// <param name="initialUri"></param>
    /// <param name="cancellationToken"></param>
    Task Crawl(Uri initialUri, CancellationToken cancellationToken);
}
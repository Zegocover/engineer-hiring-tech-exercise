using System.Net.Http.Headers;
using System.Net.Mime;

using Microsoft.Extensions.Logging;

namespace CrawlerApp.Services;

public class UriContentService(HttpClient httpClient, ILogger<UriContentService> logger) : IUriContentService
{
    /// <inheritdoc />
    public async Task<string?> GetHtmlContent(Uri uri, CancellationToken cancellationToken)
    {
        try
        {
            HttpRequestMessage request = new() { RequestUri = uri };
            request.Headers.Accept.Add(new MediaTypeWithQualityHeaderValue(MediaTypeNames.Text.Html));
            var response = await httpClient.SendAsync(request, cancellationToken);
            response.EnsureSuccessStatusCode();
            if (response.Content.Headers.ContentType!.MediaType == MediaTypeNames.Text.Html)
            {
                return await response.Content.ReadAsStringAsync(cancellationToken);
            }

            logger.LogError("Failed to retrieve content for uri {uri}. Content is not html", uri.AbsoluteUri);
            return null;
        }
        catch (Exception e)
        {
            logger.LogError("Failed to retrieve content for uri {uri}. Error: {message}", uri.AbsoluteUri, e.Message);
            return null;
        }
    }
}

public interface IUriContentService
{
    /// <summary>
    ///     Gets HTML content for a given uri. Returns null if html content not found.
    /// </summary>
    /// <param name="uri"></param>
    /// <param name="cancellationToken"></param>
    /// <returns></returns>
    Task<string?> GetHtmlContent(Uri uri, CancellationToken cancellationToken);
}
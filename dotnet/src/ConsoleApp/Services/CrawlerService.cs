using System;
using System.Collections.Concurrent;
using System.Linq;
using System.Threading;
using System.Threading.Channels;
using System.Threading.Tasks;
using AngleSharp;
using AngleSharp.Dom;
using AngleSharp.Html.Dom;
using ConsoleApp.Extensions;
using Spectre.Console;

namespace ConsoleApp.Services;

internal sealed class CrawlerService
{
    private readonly IConfiguration _contextConfiguration = Configuration.Default.WithDefaultLoader();
    private readonly Channel<string> _channel = Channel.CreateUnbounded<string>();
    private readonly ConcurrentDictionary<string, byte> _visitedUris = new();

    private int CurrentCount = 0;

    public async Task StartAsync(string url, int maxConnections, CancellationToken cancellationToken)
    {
        await Enqueue(url);

        var host = new Uri(url).Host;

        var tasks = Enumerable.Range(0, maxConnections).Select(_ => WorkAsync(host, cancellationToken)).ToArray();

        await Task.WhenAll(tasks);

        Console.WriteLine("Crawling completed.");
    }

    private async Task Enqueue(string uri)
    {
        var normalizedUri = NormalizeUri(uri);

        if (_visitedUris.TryAdd(normalizedUri, 0) is false)
            return;

        Interlocked.Increment(ref CurrentCount);

        _ = _channel.Writer.TryWrite(normalizedUri);
    }

    private async Task WorkAsync(string originalHost, CancellationToken cancellationToken)
    {
        await foreach (var uri in _channel.Reader.ReadAllAsync(cancellationToken))
        {
            try
            {
                var links = await GetLinksAsync(uri, cancellationToken);

                var body = links.Length > 0 ? $"\n - {string.Join("\n - ", links)}" : string.Empty;

                AnsiConsole.MarkupLineInterpolated($"[green]## {uri} ##[/]{body}\n");

                foreach (var link in links)
                    if (link.IsSameHostUri(originalHost))
                        await Enqueue(link);
            }
            catch (Exception ex)
            {
                AnsiConsole.MarkupLineInterpolated($"[red]## {uri} ## - Error: {ex.Message.EscapeMarkup()}[/]\n");
            }
            finally
            {
                if (Interlocked.Decrement(ref CurrentCount) == 0)
                    _ = _channel.Writer.TryComplete();
            }
        }
    }

    private async Task<string[]> GetLinksAsync(string uri, CancellationToken cancellationToken)
    {
        var context = BrowsingContext.New(_contextConfiguration);

        var document = await context.OpenAsync(uri, cancellationToken);

        return ExtractLinks(document);
    }

    private static string[] ExtractLinks(IDocument document)
    {
        return [.. document
            .QuerySelectorAll("a")
            .OfType<IHtmlAnchorElement>()
            .Select(x => x.Href)
            .Where(x => x.HasValue())
            .Distinct()];
    }

    private static string NormalizeUri(string uri)
    {
        return uri.Length > 1 && uri[^1] == '/' && uri[^2] != '/' ? uri[..^1] : uri;
    }
}

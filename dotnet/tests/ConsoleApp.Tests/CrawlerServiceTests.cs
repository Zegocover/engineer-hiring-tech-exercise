using System;
using System.Threading;
using System.Threading.Tasks;
using ConsoleApp.Services;
using Spectre.Console;
using Spectre.Console.Testing;

namespace ConsoleApp.Tests;

[Collection("Stub site")]
public class CrawlerServiceTests(StubSiteFixture site)
{
    private string RootPageUrl => site.BaseUrl.TrimEnd('/');

    private async Task<string> CrawlAsync()
    {
        var testConsole = new TestConsole();
        AnsiConsole.Console = testConsole;

        try
        {
            var service = new CrawlerService();

            using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(30));

            await service.StartAsync(site.BaseUrl, maxConnections: 4, cts.Token);

            return testConsole.Output;
        }
        finally
        {
            AnsiConsole.Console = AnsiConsole.Create(new AnsiConsoleSettings());
        }
    }

    private static int CountOccurrences(string haystack, string needle)
    {
        var count = 0;
        var index = 0;

        while ((index = haystack.IndexOf(needle, index, StringComparison.Ordinal)) != -1)
        {
            count++;
            index += needle.Length;
        }

        return count;
    }

    [Fact(DisplayName = "Crawl visits every same-domain page and prints its URL")]
    public async Task VisitsEverySameDomainPage()
    {
        // Act
        var output = await CrawlAsync();

        // Assert
        Assert.Contains($"## {RootPageUrl} ##", output);
        Assert.Contains($"## {site.BaseUrl}contacts.html ##", output);
        Assert.Contains($"## {site.BaseUrl}help.html ##", output);
        Assert.Contains($"## {site.BaseUrl}pricing.html ##", output);
        Assert.Contains($"## {site.BaseUrl}faq.html ##", output);
    }

    [Fact(DisplayName = "Crawl discovers pages more than one link deep")]
    public async Task DiscoversPagesMultipleLinksDeep()
    {
        // Act
        var output = await CrawlAsync();

        // Assert: faq.html is only ever linked to from pricing.html, never from the seed page
        Assert.Equal(1, CountOccurrences(output, $"## {site.BaseUrl}faq.html ##"));
    }

    [Fact(DisplayName = "Crawl prints external and subdomain links but never follows them")]
    public async Task PrintsButDoesNotFollowOtherHosts()
    {
        // Act
        var output = await CrawlAsync();

        // Assert
        Assert.Contains("https://othersite.example/never-visit", output);
        Assert.Contains("http://sub.localhost/never-visit", output);
        Assert.DoesNotContain("## https://othersite.example/never-visit ##", output);
        Assert.DoesNotContain("## http://sub.localhost/never-visit ##", output);
    }

    [Fact(DisplayName = "Crawl visits a page once despite being linked from a duplicate anchor and from a page two hops deep")]
    public async Task VisitsRepeatedLinkOnce()
    {
        // Act
        var output = await CrawlAsync();

        // Assert: pricing.html is linked twice from index.html and once more from faq.html
        Assert.Equal(1, CountOccurrences(output, $"## {site.BaseUrl}pricing.html ##"));
    }

    [Fact(DisplayName = "Crawl treats a trailing-slash variant of an already-queued URL as the same page")]
    public async Task TreatsTrailingSlashVariantAsSamePage()
    {
        // Act
        var output = await CrawlAsync();

        // Assert
        Assert.Equal(1, CountOccurrences(output, $"## {site.BaseUrl}help.html ##"));
        Assert.DoesNotContain($"## {site.BaseUrl}help.html/ ##", output);
    }

    [Fact(DisplayName = "Crawl does not revisit the seed page when a discovered page links back to it")]
    public async Task DoesNotRevisitSeedPage()
    {
        // Act
        var output = await CrawlAsync();

        // Assert
        Assert.Equal(1, CountOccurrences(output, $"## {RootPageUrl} ##"));
    }
}

using System.Diagnostics;

using CrawlerApp.Configuration;
using CrawlerApp.Services;
using CrawlerApp.Startup;

using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

var builder = Host.CreateDefaultBuilder();

builder.AddConfiguration(args)
    .AddServices();

var host = builder.Build();

// Use the logger from DI instead of Console.WriteLine
var logger = host.Services.GetRequiredService<ILogger<Program>>();

var urisToCrawl = host.Services.GetRequiredService<CrawlerAppOptions>().Uri;
if (urisToCrawl.Count == 0)
{
    logger.LogWarning("No URLs provided. Exiting.");
    return;
}

var crawlerService = host.Services.GetRequiredService<ICrawlerService>();

foreach (var uri in urisToCrawl)
{
    await crawlerService.Crawl(uri, CancellationToken.None);
}

var stopWatch = Stopwatch.StartNew();

stopWatch.Stop();
#pragma warning disable CA1873
logger.LogInformation("Completed in : {time}ms", stopWatch.ElapsedMilliseconds);
#pragma warning restore CA1873
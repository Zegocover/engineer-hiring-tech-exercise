using System;
using ConsoleApp.Commands;
using ConsoleApp.Constants;
using ConsoleApp.Extensions;
using ConsoleApp.Services;
using Microsoft.Extensions.DependencyInjection;
using Spectre.Console;
using Spectre.Console.Cli;

try
{
    var app = CommandApp.CreateWithServices<CrawlCommand>(services =>
        services.AddSingleton<CrawlerService>());

    app.Configure(config => config.SetApplicationName("crawler"));

    app.WithDescription("Crawls a website starting from a URL, printing every link found on each page, and only following links on the same host (excluding other domains and subdomains).");

    return app.Run(args);
}
catch (Exception ex)
{
    AnsiConsole.WriteException(ex);

    return AppReturnCodes.WithError;
}

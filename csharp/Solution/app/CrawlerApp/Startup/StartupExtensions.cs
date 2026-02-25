using System.Net.Http.Headers;
using System.Net.Mime;

using CrawlerApp.Configuration;
using CrawlerApp.Services;

using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

namespace CrawlerApp.Startup;

public static class StartupExtensions
{
    /// <summary>
    ///     Configures settings for the application such as the command line arguments
    /// </summary>
    /// <param name="builder"></param>
    /// <param name="args"></param>
    /// <returns></returns>
    public static IHostBuilder AddConfiguration(this IHostBuilder builder, string[] args)
    {
        builder.ConfigureAppConfiguration((_, config) =>
        {
            ArgumentParser.ParseUriArgs(config, args);
        });
        return builder;
    }

    /// <summary>
    ///     Adds service dependencies required to run the application
    /// </summary>
    /// <param name="builder"></param>
    /// <returns></returns>
    public static IHostBuilder AddServices(this IHostBuilder builder)
    {
        builder.ConfigureServices((context, services) =>
        {
            var config = context.Configuration;
            var options = new CrawlerAppOptions();
            config.Bind(options);

            // ...existing code...
            options.Uri = options.Uri
                .Where(uri => Uri.IsWellFormedUriString(uri.ToString(), UriKind.Absolute))
                .Select(uri => new Uri(uri.ToString()))
                .ToList();

            services.AddSingleton(options);

            services.AddHttpClient<UriContentService>(client =>
            {
                client.DefaultRequestHeaders.Accept.Add(
                    new MediaTypeWithQualityHeaderValue(MediaTypeNames.Text.Html));
            });
            services.AddMemoryCache();
            services.AddSingleton<IUriContentService, UriContentService>();
            services.AddSingleton<ICrawlerService, CrawlerService>();
            services.AddLogging(configure => configure.AddConsole());
        });
        return builder;
    }
}
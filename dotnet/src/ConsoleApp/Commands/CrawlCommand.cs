using System.ComponentModel;
using ConsoleApp.Constants;
using ConsoleApp.Services;
using Spectre.Console;
using Spectre.Console.Cli;
using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using System.Threading;

namespace ConsoleApp.Commands;

internal sealed class CrawlCommand(CrawlerService service) : AsyncCommand<CrawlCommand.Settings>
{
    internal sealed class Settings : CommandSettings
    {
        [CommandArgument(0, "<uri>")]
        [Description("The URI to crawl.")]
        public required string InitialUrl { get; set; }

        [CommandOption("-m|--max-connections <maxConnections>")]
        [Description("The maximum number of concurrent connections. Defaults to 10.")]
        public int MaxConnections { get; set; } = 10;

        public bool InitialUrlIsValid()
        {
            return Uri.TryCreate(InitialUrl, UriKind.Absolute, out var uri) &&
                (uri.Scheme == Uri.UriSchemeHttp || uri.Scheme == Uri.UriSchemeHttps);
        }

        public override ValidationResult Validate()
        {
            var result = base.Validate();

            if (!result.Successful)
                return result;

            var errors = new List<string>();

            if (!InitialUrlIsValid())
                errors.Add("Invalid URI.");

            if (MaxConnections <= 0)
                errors.Add("MaxConnections must be greater than 0.");

            return errors.Count > 0
                ? ValidationResult.Error(string.Join(Environment.NewLine, errors))
                : ValidationResult.Success();
        }
    }

    protected override async Task<int> ExecuteAsync(CommandContext context, Settings settings, CancellationToken cancellationToken)
    {
        AnsiConsole.MarkupLineInterpolated($"[yellow]Starting the crawl on \"{settings.InitialUrl}\".[/]");

        await service.StartAsync(settings.InitialUrl, settings.MaxConnections, cancellationToken);

        return AppReturnCodes.Success;
    }
}

using Microsoft.Extensions.Configuration;

namespace CrawlerApp.Startup;

public static class ArgumentParser
{
    /// <summary>
    /// Parses the uri command line arguments while preserving other arguments so they do not get removed.
    /// </summary>
    /// <param name="config"></param>
    /// <param name="args"></param>
    public static void ParseUriArgs(IConfigurationBuilder config, string[] args)
    {
        // Collect repeated --uri <value> arguments and convert to indexed keys expected by the binder
        var uriValues = new List<string>();
        var remainingArgs = new List<string>();

        for (int i = 0; i < args.Length; i++)
        {
            var a = args[i];
            // Only support the simple repeated form: --uri <value>
            if (a.Equals("--uri", StringComparison.OrdinalIgnoreCase) && i + 1 < args.Length)
            {
                uriValues.Add(args[i + 1]);
                i++; // skip the value
            }
            else
            {
                remainingArgs.Add(a);
            }
        }

        if (uriValues.Count > 0)
        {
            var dict = new Dictionary<string, string?>(StringComparer.OrdinalIgnoreCase);
            for (int i = 0; i < uriValues.Count; i++)
            {
                // Provide indexed keys that the binder binds to when binding root -> CrawlerAppOptions
                dict[$"Uri:{i}"] = uriValues[i];
            }

            config.AddInMemoryCollection(dict);
        }

        // Add back remaining args so other command-line options still work
        if (remainingArgs.Count > 0)
        {
            config.AddCommandLine(remainingArgs.ToArray());
        }
    }
}
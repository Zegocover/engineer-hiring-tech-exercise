using System;
using System.Diagnostics.CodeAnalysis;

namespace ConsoleApp.Extensions;

internal static class StringExtensions
{
    public static bool HasValue([NotNullWhen(true)] this string? str)
    {
        return string.IsNullOrWhiteSpace(str) is false;
    }

    public static bool IsEqual(this string left, string right, bool ignoreCase = true)
    {
        return string.Equals(left, right, ignoreCase ? StringComparison.InvariantCultureIgnoreCase : StringComparison.InvariantCulture);
    }

    public static bool IsSameHostUri(this string uri, string host)
    {
        try
        {
            var uriHost = new Uri(uri).Host;

            return uriHost.IsEqual(host);
        }
        catch (UriFormatException)
        {
            return false;
        }
    }
}

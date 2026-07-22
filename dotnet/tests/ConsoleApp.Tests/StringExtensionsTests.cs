using ConsoleApp.Extensions;

namespace ConsoleApp.Tests;

public class StringExtensionsTests
{
    [Fact(DisplayName = "HasValue returns false for null, empty or whitespace strings")]
    public void HasValueReturnsFalseForNullOrBlank()
    {
        // Arrange
        string? nullValue = null;

        // Act
        var nullResult = nullValue.HasValue();
        var emptyResult = "".HasValue();
        var whitespaceResult = "   ".HasValue();

        // Assert
        Assert.False(nullResult);
        Assert.False(emptyResult);
        Assert.False(whitespaceResult);
    }

    [Fact(DisplayName = "HasValue returns true for a non-empty string")]
    public void HasValueReturnsTrueForNonEmptyString()
    {
        // Arrange
        var value = "https://coolwebsite.com/";

        // Act
        var result = value.HasValue();

        // Assert
        Assert.True(result);
    }

    [Fact(DisplayName = "IsEqual ignores case by default")]
    public void IsEqualIgnoresCaseByDefault()
    {
        // Arrange
        var left = "COOLWEBSITE.com";
        var right = "coolwebsite.COM";

        // Act
        var result = left.IsEqual(right);

        // Assert
        Assert.True(result);
    }

    [Fact(DisplayName = "IsEqual respects case when ignoreCase is false")]
    public void IsEqualRespectsCaseWhenRequested()
    {
        // Arrange
        var left = "COOLWEBSITE.com";
        var right = "coolwebsite.com";

        // Act
        var result = left.IsEqual(right, ignoreCase: false);

        // Assert
        Assert.False(result);
    }

    [Fact(DisplayName = "IsSameHostUri returns true when the hosts match")]
    public void IsSameHostUriReturnsTrueForMatchingHost()
    {
        // Arrange
        var uri = "https://coolwebsite.com/cli";
        var host = "coolwebsite.com";

        // Act
        var result = uri.IsSameHostUri(host);

        // Assert
        Assert.True(result);
    }

    [Fact(DisplayName = "IsSameHostUri returns false for a different subdomain")]
    public void IsSameHostUriReturnsFalseForDifferentSubdomain()
    {
        // Arrange
        var uri = "https://blog.coolwebsite.com/post";
        var host = "coolwebsite.com";

        // Act
        var result = uri.IsSameHostUri(host);

        // Assert
        Assert.False(result);
    }

    [Fact(DisplayName = "IsSameHostUri returns false instead of throwing for a relative or malformed URI")]
    public void IsSameHostUriReturnsFalseForRelativeUri()
    {
        // Arrange
        var uri = "/console";
        var host = "coolwebsite.com";

        // Act
        var result = uri.IsSameHostUri(host);

        // Assert
        Assert.False(result);
    }
}

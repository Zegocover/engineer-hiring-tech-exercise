using CrawlerApp.Configuration;
using CrawlerApp.Startup;
using Microsoft.Extensions.Configuration;

namespace Tests.App;

public class ArgumentParserTests
{
    [Fact]
    public void Parse_WhenSingleUriPassed_ParsesUriSuccessfully()
    {
        // Arrange
        var args = new[] { "--uri", "https://example.com" };
        var configBuilder = new ConfigurationBuilder();

        // Act
        ArgumentParser.ParseUriArgs(configBuilder, args);
        var config = configBuilder.Build();

        // Assert
        var options = new CrawlerAppOptions();
        config.Bind(options);
        
        Assert.NotNull(options.Uri);
        Assert.Single(options.Uri);
        Assert.Equal(new Uri("https://example.com"), options.Uri[0]);
    }
    
    [Fact]
    public void Parse_WhenMultipleUrisPassed_ParsesUris_Successfully()
    {
        // Arrange
        var args = new[] 
        { 
            "--uri", "https://example.com",
            "--uri", "https://example.org",
            "--uri", "https://example.net"
        };
        var configBuilder = new ConfigurationBuilder();

        // Act
        ArgumentParser.ParseUriArgs(configBuilder, args);
        var config = configBuilder.Build();

        // Assert
        var options = new CrawlerAppOptions();
        config.Bind(options);
        
        Assert.NotNull(options.Uri);
        Assert.Equal(3, options.Uri.Count);
        Assert.Equal(new Uri("https://example.com"), options.Uri[0]);
        Assert.Equal(new Uri("https://example.org"), options.Uri[1]);
        Assert.Equal(new Uri("https://example.net"), options.Uri[2]);
    }

    [Fact]
    public void Parse_WhenInvalidUrisPassed_InvalidUrisNotFiltered()
    {
        // Arrange
        var args = new[] 
        { 
            "--uri", "https://example.com",
            "--uri", "not a valid uri",
            "--uri", "https://valid.com"
        };
        var configBuilder = new ConfigurationBuilder();

        // Act
        ArgumentParser.ParseUriArgs(configBuilder, args);
        var config = configBuilder.Build();

        // Assert
        var options = new CrawlerAppOptions();
        config.Bind(options);
        
        // All three URIs should be bound (filtering happens in StartupExtensions)
        Assert.NotNull(options.Uri);
        Assert.Equal(3, options.Uri.Count);
    }
}
# CSharp Solution

A C# implementation of a console application that crawls a base URL, only following valid links within that domain. The crawler respects domain boundaries and does not process subdomains or external domains.

## Structure

- [Solution](./Solution/) - Main solution directory
- [Solution/app](./Solution/app/) - Application directory containing the CrawlerApp
- [Solution/Tests](./Solution/Tests/) - Test directory containing comprehensive unit tests

## Design

The solution follows SOLID principles with a clean separation of concerns:

- **CrawlerService**: Core crawler implementation with domain boundary enforcement
- **UriContentService**: HTTP client for retrieving HTML content from URIs
- **In-Memory Cache**: Thread-safe cache (IMemoryCache) for tracking visited URIs to prevent duplicate crawls
- **Flexible CLI**: Supports multiple URI arguments via repeated `--uri` flags for crawling multiple domains

### Learning & Technologies
- **HTML Link Parsing**: Developed understanding of HTML link syntax and anchor tag structure (`<a href="...">`) to correctly extract and validate URLs from web pages
- **HtmlAgilityPack**: Leveraged this library for DOM traversal and XPath queries to parse HTML content and extract valid hyperlinks from crawled pages

## How to Run

### Prerequisites
- .NET 10.0 or later see [`global.json`](./Solution/global.json)
- Command line/Terminal access

### Crawl Application
Navigate to the Solution directory, then run the app with one or more URIs:

#### Single URL
```bash
cd Solution/app/CrawlerApp
dotnet run --uri http://example.com
```

#### Multiple URLs
```bash
cd Solution/app/CrawlerApp
dotnet run --uri http://example.com --uri http://example.org --uri http://example.net
```

### Run Tests

From the Solution directory:

```bash
cd Solution
dotnet test
```

This will execute all unit tests.

## Development Tools & Technologies

### IDE
- JetBrains Rider

### Testing Framework
- xUnit with NSubstitute for mocking
- AwesomeAssertions for fluent assertions

### AI Tools
- Claude Haiku 4.5 (GitHub Copilot) for:
  - Test case generation and data setup
  - Code documentation and README writing
  - Code review and improvements

## Code Quality
- **EditorConfig**: Enforces dotnet standards for formatting. (generated using dotnet cli)
- **Logging**: Structured logging with ILogger and source-generated log messages
- **Test Coverage**: Comprehensive unit tests covering:
  - CLI argument parsing (single/multiple URIs, invalid URIs)
  - Crawler domain boundary enforcement (same domain, subdomain rejection, external domain rejection)
  - HTTP response handling (valid HTML, invalid content-type, failed requests)
  - Cache behavior (duplicate URI prevention)

## Future Enhancements
- More testing
- Support for additional crawl modes (include subdomains, follow external links)
- Export crawl results to various formats (JSON, CSV)

package crawler

import (
	"context"
	"testing"
	"time"

	"webcrawler/internal/fetcher"
)

func TestCrawler_BasicCrawl(t *testing.T) {
	mock := fetcher.NewMockFetcher()

	// Set up a simple site structure
	mock.AddHTMLResponse("https://example.com/", `
		<html>
		<body>
			<a href="/page1">Page 1</a>
			<a href="/page2">Page 2</a>
		</body>
		</html>
	`)

	mock.AddHTMLResponse("https://example.com/page1", `
		<html>
		<body>
			<a href="/">Home</a>
			<a href="/page2">Page 2</a>
		</body>
		</html>
	`)

	mock.AddHTMLResponse("https://example.com/page2", `
		<html>
		<body>
			<a href="/">Home</a>
			<a href="/page1">Page 1</a>
			<a href="https://external.com">External</a>
		</body>
		</html>
	`)

	opts := DefaultOptions()
	opts.Workers = 2
	opts.RateLimit = 100

	c, err := NewWithFetcher("https://example.com/", opts, mock)
	if err != nil {
		t.Fatalf("Failed to create crawler: %v", err)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	results := c.Run(ctx)

	crawledURLs := make(map[string]bool)
	for result := range results {
		crawledURLs[result.URL] = true
	}

	// Should have crawled all 3 pages
	expectedURLs := []string{
		"https://example.com/",
		"https://example.com/page1",
		"https://example.com/page2",
	}

	for _, url := range expectedURLs {
		if !crawledURLs[url] {
			t.Errorf("expected to crawl %s", url)
		}
	}

	if len(crawledURLs) != 3 {
		t.Errorf("expected 3 URLs crawled, got %d", len(crawledURLs))
	}
}

func TestCrawler_MaxURLs(t *testing.T) {
	mock := fetcher.NewMockFetcher()

	// Set up pages that link to many others
	mock.AddHTMLResponse("https://example.com/", `
		<html>
		<body>
			<a href="/page1">Page 1</a>
			<a href="/page2">Page 2</a>
			<a href="/page3">Page 3</a>
			<a href="/page4">Page 4</a>
			<a href="/page5">Page 5</a>
		</body>
		</html>
	`)

	for i := 1; i <= 5; i++ {
		mock.AddHTMLResponse("https://example.com/page"+string(rune('0'+i)), `<html><body>Page</body></html>`)
	}

	opts := DefaultOptions()
	opts.Workers = 1
	opts.MaxURLs = 3
	opts.RateLimit = 100

	c, err := NewWithFetcher("https://example.com/", opts, mock)
	if err != nil {
		t.Fatalf("Failed to create crawler: %v", err)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	results := c.Run(ctx)

	count := 0
	for range results {
		count++
	}

	if count > 3 {
		t.Errorf("expected at most 3 URLs crawled, got %d", count)
	}
}

func TestCrawler_ExternalLinks(t *testing.T) {
	mock := fetcher.NewMockFetcher()

	mock.AddHTMLResponse("https://example.com/", `
		<html>
		<body>
			<a href="https://external1.com">External 1</a>
			<a href="https://external2.com">External 2</a>
			<a href="/internal">Internal</a>
		</body>
		</html>
	`)

	mock.AddHTMLResponse("https://example.com/internal", `
		<html>
		<body>Content</body>
		</html>
	`)

	opts := DefaultOptions()
	opts.Workers = 1
	opts.RateLimit = 100

	c, err := NewWithFetcher("https://example.com/", opts, mock)
	if err != nil {
		t.Fatalf("Failed to create crawler: %v", err)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	results := c.Run(ctx)

	var homeResult *Result
	for result := range results {
		if result.URL == "https://example.com/" {
			homeResult = result
			break
		}
	}

	// Drain remaining results
	for range results {
	}

	if homeResult == nil {
		t.Fatal("expected to find home page result")
	}

	// External links should be in External slice
	if len(homeResult.External) != 2 {
		t.Errorf("expected 2 external links, got %d", len(homeResult.External))
	}

	// Internal links should be in SameHost slice
	if len(homeResult.SameHost) != 1 {
		t.Errorf("expected 1 internal link, got %d", len(homeResult.SameHost))
	}
}

func TestCrawler_InvalidURL(t *testing.T) {
	opts := DefaultOptions()

	_, err := New("not-a-valid-url", opts)
	if err == nil {
		t.Error("expected error for invalid URL")
	}

	_, err = New("ftp://example.com", opts)
	if err == nil {
		t.Error("expected error for non-HTTP URL")
	}
}

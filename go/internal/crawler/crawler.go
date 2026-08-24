package crawler

import (
	"context"
	"fmt"
	"io"
	"log"
	"mime"
	"net/http"
	"net/url"
	"strings"
	"sync"
	"time"

	"github.com/rijude/single-domain-crawler/go/internal/logging"
	"golang.org/x/net/html"
)

const (
	// RequestBufferSize is the maximum number of URLs that can be queued for processing.
	RequestBufferSize = 1000
	// maxResponseBytes is the maximum number of bytes read from a response body.
	maxResponseBytes = 2 << 20
	// requestTimeout is the maximum time allowed for a request to complete.
	requestTimeout = 15 * time.Second
	// maxFetchAttempts is the maximum number of attempts for one URL.
	maxFetchAttempts = 3
	// fetchRetryBackoff is the delay before the first retry.
	fetchRetryBackoff = 100 * time.Millisecond
)

// Crawler fetches a URL and recursively crawls same-host links.
type Crawler struct {
	client *http.Client
	logger *logging.Logger
}

// result contains the outcome of processing one URL and its discovered links.
type result struct {
	url   string
	links []string
	err   error
}

// New returns a crawler that discards logs and reports only error-level events.
func New() *Crawler {
	return NewWithLogger(log.New(io.Discard, "", 0), logging.ErrorLevel)
}

// NewWithLogger returns a crawler configured with the provided logger and level.
func NewWithLogger(logger *log.Logger, level logging.LogLevel) *Crawler {
	return &Crawler{
		client: &http.Client{Timeout: requestTimeout},
		logger: logging.NewLogger(logger, level),
	}
}

// Crawl fetches the start URL and recursively crawls same-host links.
func (crawler *Crawler) Crawl(ctx context.Context, startURL string, workers int) ([]string, error) {
	if workers < 1 {
		return nil, fmt.Errorf("workers must be at least 1")
	}

	seed, err := normalizeURL(startURL)
	if err != nil {
		return nil, err
	}
	seedHost := seed.Hostname()
	crawlClient := *crawler.client
	crawlClient.CheckRedirect = func(redirectRequest *http.Request, _ []*http.Request) error {
		if redirectRequest.URL.Hostname() != seedHost {
			return http.ErrUseLastResponse
		}
		return nil
	}

	requests := make(chan string, RequestBufferSize)
	results := make(chan result, workers)

	var workerGroup sync.WaitGroup
	workerGroup.Add(workers)
	for range workers {
		go func() {
			defer workerGroup.Done()
			crawler.worker(ctx, requests, results, &crawlClient, seedHost)
		}()
	}

	seedURL := seed.String()
	// queued contains URLs waiting to be sent to a worker.
	queued := []string{seedURL}
	// scheduled prevents the same URL from being queued more than once.
	scheduled := map[string]struct{}{seedURL: {}}
	// processingURLs counts requests sent to workers without a received result.
	processingURLs := 0
	// urls contains every URL whose processing has completed.
	urls := make([]string, 0)

	for len(queued) > 0 || processingURLs > 0 {

		// sendRequests is nil when there are no queued URLs, which disables the send case.
		var sendRequests chan string
		var nextURL string
		if len(queued) > 0 {
			sendRequests = requests
			nextURL = queued[0]
		}

		select {
		case sendRequests <- nextURL:
			queued = queued[1:]
			processingURLs++
		case crawlResult := <-results:
			processingURLs--
			urls = append(urls, crawlResult.url)
			// If the seed URL failed, stop crawling and return the error.
			if crawlResult.url == seedURL && crawlResult.err != nil {
				close(requests)
				workerGroup.Wait()
				return urls, crawlResult.err
			}
			queued = scheduleLinks(queued, scheduled, crawlResult.links)
		case <-ctx.Done():
			return urls, ctx.Err()
		}
	}

	close(requests)
	workerGroup.Wait()
	return urls, nil
}

// scheduleLinks adds new links to the queue and filters already scheduled URLs.
func scheduleLinks(queued []string, scheduled map[string]struct{}, links []string) []string {
	for _, link := range links {
		if _, exists := scheduled[link]; exists {
			continue
		}
		scheduled[link] = struct{}{}
		queued = append(queued, link)
	}
	return queued
}

// worker processes URLs from requests and reports their results.
func (crawler *Crawler) worker(ctx context.Context, requests <-chan string, results chan<- result, client *http.Client, seedHost string) {
	for {
		var requestURL string
		var open bool
		select {
		case requestURL, open = <-requests:
			if !open {
				return
			}
		case <-ctx.Done():
			return
		}

		crawler.logger.Debugf("worker processing URL: %s", requestURL)
		links, fetchErr := crawler.fetchWithRetries(ctx, client, requestURL, seedHost)
		if fetchErr != nil {
			crawler.logger.Errorf("failed to process URL %s: %v", requestURL, fetchErr)
		}
		select {
		case results <- result{url: requestURL, links: links, err: fetchErr}:
		case <-ctx.Done():
			return
		}
	}
}

// fetchWithRetries retrieves a URL, retrying transient failures when appropriate.
func (crawler *Crawler) fetchWithRetries(ctx context.Context, client *http.Client, rawURL, seedHost string) ([]string, error) {
	for attempt := 1; attempt <= maxFetchAttempts; attempt++ {
		links, retryable, fetchErr := crawler.fetch(ctx, client, rawURL, seedHost)
		if fetchErr == nil || !retryable || attempt == maxFetchAttempts {
			return links, fetchErr
		}

		timer := time.NewTimer(fetchRetryBackoff * time.Duration(attempt))
		select {
		case <-timer.C:
		case <-ctx.Done():
			timer.Stop()
			return nil, ctx.Err()
		}
	}

	return nil, ctx.Err()
}

// fetch makes one request and reports whether its error may be retried.
func (crawler *Crawler) fetch(ctx context.Context, client *http.Client, rawURL, seedHost string) ([]string, bool, error) {
	request, err := http.NewRequestWithContext(ctx, http.MethodGet, rawURL, nil)
	if err != nil {
		return nil, false, err
	}
	response, err := client.Do(request)
	if err != nil {
		return nil, ctx.Err() == nil, err
	}
	defer response.Body.Close()

	if response.Request.URL.Hostname() != seedHost {
		return nil, false, fmt.Errorf("redirected outside target domain")
	}
	if response.StatusCode < http.StatusOK || response.StatusCode >= http.StatusMultipleChoices {
		return nil, isRetryableStatus(response.StatusCode), fmt.Errorf("unexpected HTTP status: %s", response.Status)
	}
	contentType := response.Header.Get("Content-Type")
	mediaType, _, parseErr := mime.ParseMediaType(contentType)
	if parseErr == nil && mediaType != "" && strings.ToLower(mediaType) != "text/html" {
		return nil, false, nil
	}

	document, err := html.Parse(io.LimitReader(response.Body, maxResponseBytes))
	if err != nil {
		return nil, false, err
	}
	base, err := url.Parse(rawURL)
	if err != nil {
		return nil, false, err
	}
	links := make([]string, 0)
	seen := make(map[string]struct{})
	var visit func(*html.Node)
	visit = func(node *html.Node) {
		if node.Type == html.ElementNode && node.Data == "a" {
			for _, attribute := range node.Attr {
				if attribute.Key != "href" {
					continue
				}
				link, linkErr := resolveURL(base, attribute.Val, seedHost)
				if linkErr == nil {
					if _, exists := seen[link]; !exists {
						seen[link] = struct{}{}
						links = append(links, link)
					}
				}
			}
		}
		for child := node.FirstChild; child != nil; child = child.NextSibling {
			visit(child)
		}
	}
	visit(document)
	return links, false, nil
}

// isRetryableStatus reports whether an HTTP status commonly indicates a transient failure.
func isRetryableStatus(statusCode int) bool {
	switch statusCode {
	case http.StatusTooManyRequests,
		http.StatusInternalServerError,
		http.StatusBadGateway,
		http.StatusServiceUnavailable,
		http.StatusGatewayTimeout:
		return true
	default:
		return false
	}
}

// normalizeURL validates an absolute HTTP(S) URL and removes its fragment.
func normalizeURL(rawURL string) (*url.URL, error) {
	parsed, err := url.Parse(strings.TrimSpace(rawURL))
	if err != nil {
		return nil, fmt.Errorf("invalid startUrl: %w", err)
	}
	if (parsed.Scheme != "http" && parsed.Scheme != "https") || parsed.Host == "" {
		return nil, fmt.Errorf("startUrl must be an absolute HTTP(S) URL")
	}
	parsed.Fragment = ""
	return parsed, nil
}

// resolveURL resolves a link against a page URL and enforces the target host.
func resolveURL(base *url.URL, rawURL, seedHost string) (string, error) {
	parsed, err := url.Parse(strings.TrimSpace(rawURL))
	if err != nil {
		return "", err
	}
	resolved := base.ResolveReference(parsed)
	if (resolved.Scheme != "http" && resolved.Scheme != "https") || resolved.Hostname() != seedHost {
		return "", fmt.Errorf("link is outside target domain")
	}
	resolved.Fragment = ""
	return resolved.String(), nil
}

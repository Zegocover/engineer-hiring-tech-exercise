package crawler

import (
	"context"
	"fmt"
	"strings"
	"sync"
	"sync/atomic"
	"time"

	"webcrawler/internal/dedup"
	"webcrawler/internal/domain"
	"webcrawler/internal/fetcher"
	"webcrawler/internal/frontier"
	"webcrawler/internal/parser"
	"webcrawler/internal/robots"
)

// Result represents the result of crawling a single page.
type Result struct {
	URL       string
	Links     []string   // All links found on page
	SameHost  []string   // Links on same domain (will be crawled)
	External  []string   // External links (printed but not crawled)
	Error     error
	Timestamp time.Time
}

// Crawler orchestrates the web crawling process.
type Crawler struct {
	opts     Options
	baseURL  string
	frontier frontier.Frontier
	dedup    dedup.Deduplicator
	fetcher  fetcher.Fetcher
	parser   *parser.Parser
	robots   *robots.Checker
	results  chan *Result
	crawled  int64
	wg       sync.WaitGroup
}

// New creates a new crawler instance.
func New(baseURL string, opts Options) (*Crawler, error) {
	// Normalize base URL
	normalizedURL, err := domain.Normalize(baseURL)
	if err != nil {
		return nil, fmt.Errorf("invalid base URL: %w", err)
	}

	if !domain.IsValidHTTP(normalizedURL) {
		return nil, fmt.Errorf("URL must be http or https")
	}

	// Create frontier
	var f frontier.Frontier
	if opts.UseRedis {
		host, _ := domain.GetHost(normalizedURL)
		rf, err := frontier.NewRedisFrontier(opts.RedisAddr, "crawler:"+host)
		if err != nil {
			return nil, fmt.Errorf("failed to connect to Redis: %w", err)
		}
		f = rf
	} else {
		f = frontier.NewMemoryFrontier(opts.FrontierCapacity)
	}

	// Create fetcher
	fetcherCfg := fetcher.Config{
		Timeout:   opts.Timeout,
		UserAgent: opts.UserAgent,
		RateLimit: opts.RateLimit,
		BurstLimit: 1,
	}
	httpFetcher := fetcher.NewHTTPFetcher(fetcherCfg)

	return &Crawler{
		opts:     opts,
		baseURL:  normalizedURL,
		frontier: f,
		dedup:    dedup.NewBloomDedup(opts.BloomExpectedItems, opts.BloomFalsePositiveRate),
		fetcher:  httpFetcher,
		parser:   parser.NewParser(),
		robots:   robots.NewChecker(opts.UserAgent),
		results:  make(chan *Result, opts.Workers*2),
	}, nil
}

// NewWithFetcher creates a crawler with a custom fetcher (for testing).
func NewWithFetcher(baseURL string, opts Options, f fetcher.Fetcher) (*Crawler, error) {
	normalizedURL, err := domain.Normalize(baseURL)
	if err != nil {
		return nil, fmt.Errorf("invalid base URL: %w", err)
	}

	return &Crawler{
		opts:     opts,
		baseURL:  normalizedURL,
		frontier: frontier.NewMemoryFrontier(opts.FrontierCapacity),
		dedup:    dedup.NewBloomDedup(opts.BloomExpectedItems, opts.BloomFalsePositiveRate),
		fetcher:  f,
		parser:   parser.NewParser(),
		robots:   robots.NewChecker(opts.UserAgent),
		results:  make(chan *Result, opts.Workers*2),
	}, nil
}

// Run starts the crawler and returns a channel of results.
func (c *Crawler) Run(ctx context.Context) <-chan *Result {
	go c.run(ctx)
	return c.results
}

func (c *Crawler) run(ctx context.Context) {
	defer close(c.results)
	defer c.frontier.Close()

	// Fetch robots.txt
	c.robots.Fetch(ctx, c.baseURL)

	// Check if crawl delay is specified and adjust rate limit
	if delay := c.robots.CrawlDelay(); delay > 0 {
		rps := 1.0 / delay.Seconds()
		if httpFetcher, ok := c.fetcher.(*fetcher.HTTPFetcher); ok {
			httpFetcher.SetRateLimit(rps, 1)
		}
	}

	// Seed the frontier with the base URL
	c.dedup.SeenOrAdd(c.baseURL)
	if err := c.frontier.Push(ctx, c.baseURL); err != nil {
		return
	}

	// Start workers
	ctx, cancel := context.WithCancel(ctx)
	defer cancel()

	c.wg.Add(c.opts.Workers)
	for i := 0; i < c.opts.Workers; i++ {
		go c.worker(ctx)
	}

	c.wg.Wait()
}

func (c *Crawler) worker(ctx context.Context) {
	defer c.wg.Done()

	for {
		// Try to claim a crawl slot using atomic CAS
		if c.opts.MaxURLs > 0 {
			for {
				current := atomic.LoadInt64(&c.crawled)
				if current >= int64(c.opts.MaxURLs) {
					return // Limit reached
				}
				// Atomically claim this slot
				if atomic.CompareAndSwapInt64(&c.crawled, current, current+1) {
					break // Successfully claimed a slot
				}
				// CAS failed, another worker claimed it, retry
			}
		}

		// Get next URL from frontier with timeout
		url, err := c.frontier.PopWithTimeout(ctx, 2*time.Second)
		if err != nil {
			// Context cancelled - release the claimed slot if we have MaxURLs limit
			if c.opts.MaxURLs > 0 {
				atomic.AddInt64(&c.crawled, -1)
			}
			return
		}
		if url == "" {
			// Check if we should stop (empty queue and no pending work)
			if c.frontier.Size() == 0 {
				// Release the claimed slot before exiting
				if c.opts.MaxURLs > 0 {
					atomic.AddInt64(&c.crawled, -1)
				}
				return
			}
			// Release slot and continue waiting for work
			if c.opts.MaxURLs > 0 {
				atomic.AddInt64(&c.crawled, -1)
			}
			continue
		}

		// Check robots.txt
		if !c.robots.IsAllowed(url) {
			// Release slot - URL was not actually crawled
			if c.opts.MaxURLs > 0 {
				atomic.AddInt64(&c.crawled, -1)
			}
			continue
		}

		// Crawl the URL (slot already claimed)
		result := c.crawlURL(ctx, url)

		// Send result
		select {
		case c.results <- result:
		case <-ctx.Done():
			return
		}
	}
}

func (c *Crawler) crawlURL(ctx context.Context, url string) *Result {
	result := &Result{
		URL:       url,
		Timestamp: time.Now(),
	}

	// Fetch the page
	fetchResult := c.fetcher.Fetch(ctx, url)
	if fetchResult.Error != nil {
		result.Error = fetchResult.Error
		return result
	}

	if fetchResult.StatusCode < 200 || fetchResult.StatusCode >= 300 {
		result.Error = fmt.Errorf("HTTP %d", fetchResult.StatusCode)
		return result
	}

	// Only parse HTML content
	contentType := strings.ToLower(fetchResult.ContentType)
	if !strings.Contains(contentType, "text/html") {
		return result
	}

	// Extract links
	links, err := c.parser.ExtractLinks(url, fetchResult.Body)
	if err != nil {
		result.Error = err
		return result
	}

	result.Links = links

	// Categorize links
	for _, link := range links {
		if domain.IsSameDomain(c.baseURL, link) {
			result.SameHost = append(result.SameHost, link)

			// Add to frontier if not seen
			if !c.dedup.SeenOrAdd(link) {
				if err := c.frontier.Push(ctx, link); err != nil {
					continue
				}
			}
		} else {
			result.External = append(result.External, link)
		}
	}

	return result
}

// CrawledCount returns the number of URLs crawled.
func (c *Crawler) CrawledCount() int64 {
	return atomic.LoadInt64(&c.crawled)
}

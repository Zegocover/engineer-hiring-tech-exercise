package robots

import (
	"context"
	"io"
	"net/http"
	"net/url"
	"sync"
	"time"

	"github.com/temoto/robotstxt"
)

// Checker handles robots.txt parsing and URL checking.
type Checker struct {
	mu         sync.RWMutex
	data       *robotstxt.RobotsData
	userAgent  string
	crawlDelay time.Duration
}

// NewChecker creates a new robots.txt checker.
func NewChecker(userAgent string) *Checker {
	return &Checker{
		userAgent: userAgent,
	}
}

// Fetch retrieves and parses the robots.txt for the given base URL.
func (c *Checker) Fetch(ctx context.Context, baseURL string) error {
	parsedURL, err := url.Parse(baseURL)
	if err != nil {
		return err
	}

	robotsURL := parsedURL.Scheme + "://" + parsedURL.Host + "/robots.txt"

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, robotsURL, nil)
	if err != nil {
		return err
	}

	req.Header.Set("User-Agent", c.userAgent)

	client := &http.Client{Timeout: 10 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		// If we can't fetch robots.txt, allow all
		c.mu.Lock()
		c.data = nil
		c.mu.Unlock()
		return nil
	}
	defer resp.Body.Close()

	// If robots.txt doesn't exist or error, allow all
	if resp.StatusCode != http.StatusOK {
		c.mu.Lock()
		c.data = nil
		c.mu.Unlock()
		return nil
	}

	body, err := io.ReadAll(io.LimitReader(resp.Body, 512*1024)) // 512KB limit
	if err != nil {
		c.mu.Lock()
		c.data = nil
		c.mu.Unlock()
		return nil
	}

	data, err := robotstxt.FromBytes(body)
	if err != nil {
		c.mu.Lock()
		c.data = nil
		c.mu.Unlock()
		return nil
	}

	c.mu.Lock()
	c.data = data

	// Extract crawl delay if specified
	group := data.FindGroup(c.userAgent)
	if group != nil && group.CrawlDelay > 0 {
		c.crawlDelay = group.CrawlDelay
	}
	c.mu.Unlock()

	return nil
}

// IsAllowed checks if the given URL is allowed for crawling.
func (c *Checker) IsAllowed(rawURL string) bool {
	c.mu.RLock()
	defer c.mu.RUnlock()

	// If no robots.txt, allow all
	if c.data == nil {
		return true
	}

	parsedURL, err := url.Parse(rawURL)
	if err != nil {
		return false
	}

	// Check against the path
	return c.data.TestAgent(parsedURL.Path, c.userAgent)
}

// CrawlDelay returns the crawl delay specified in robots.txt.
func (c *Checker) CrawlDelay() time.Duration {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return c.crawlDelay
}

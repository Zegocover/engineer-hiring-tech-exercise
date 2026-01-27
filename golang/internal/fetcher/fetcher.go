package fetcher

import (
	"context"
	"io"
	"net/http"
	"time"

	"golang.org/x/time/rate"
)

// Result represents the result of fetching a URL.
type Result struct {
	URL         string
	StatusCode  int
	Body        []byte
	ContentType string
	Error       error
}

// Fetcher handles HTTP requests with rate limiting.
type Fetcher interface {
	Fetch(ctx context.Context, url string) *Result
}

// HTTPFetcher is a rate-limited HTTP fetcher.
type HTTPFetcher struct {
	client      *http.Client
	limiter     *rate.Limiter
	userAgent   string
	maxBodySize int64
}

// Config holds fetcher configuration.
type Config struct {
	Timeout     time.Duration
	UserAgent   string
	RateLimit   float64 // requests per second
	BurstLimit  int
	MaxBodySize int64
}

// DefaultConfig returns the default fetcher configuration.
func DefaultConfig() Config {
	return Config{
		Timeout:     30 * time.Second,
		UserAgent:   "GoCrawler/1.0",
		RateLimit:   5.0,
		BurstLimit:  1,
		MaxBodySize: 10 * 1024 * 1024, // 10MB
	}
}

// NewHTTPFetcher creates a new HTTP fetcher with rate limiting.
func NewHTTPFetcher(cfg Config) *HTTPFetcher {
	maxBodySize := cfg.MaxBodySize
	if maxBodySize <= 0 {
		maxBodySize = 10 * 1024 * 1024 // Default to 10MB
	}
	return &HTTPFetcher{
		client: &http.Client{
			Timeout: cfg.Timeout,
			CheckRedirect: func(req *http.Request, via []*http.Request) error {
				if len(via) >= 10 {
					return http.ErrUseLastResponse
				}
				return nil
			},
		},
		limiter:     rate.NewLimiter(rate.Limit(cfg.RateLimit), cfg.BurstLimit),
		userAgent:   cfg.UserAgent,
		maxBodySize: maxBodySize,
	}
}

// Fetch retrieves the content at the given URL.
func (f *HTTPFetcher) Fetch(ctx context.Context, url string) *Result {
	result := &Result{URL: url}

	// Wait for rate limiter
	if err := f.limiter.Wait(ctx); err != nil {
		result.Error = err
		return result
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		result.Error = err
		return result
	}

	req.Header.Set("User-Agent", f.userAgent)
	req.Header.Set("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")

	resp, err := f.client.Do(req)
	if err != nil {
		result.Error = err
		return result
	}
	defer resp.Body.Close()

	result.StatusCode = resp.StatusCode
	result.ContentType = resp.Header.Get("Content-Type")

	// Only read body for successful HTML responses
	if resp.StatusCode >= 200 && resp.StatusCode < 300 {
		body, err := io.ReadAll(io.LimitReader(resp.Body, f.maxBodySize))
		if err != nil {
			result.Error = err
			return result
		}
		result.Body = body
	}

	return result
}

// SetRateLimit updates the rate limiter.
func (f *HTTPFetcher) SetRateLimit(rps float64, burst int) {
	f.limiter.SetLimit(rate.Limit(rps))
	f.limiter.SetBurst(burst)
}

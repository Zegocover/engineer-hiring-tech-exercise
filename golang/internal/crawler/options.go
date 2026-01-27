package crawler

import (
	"time"
)

// Options configures the crawler behavior.
type Options struct {
	// Workers is the number of concurrent workers.
	Workers int

	// RateLimit is requests per second.
	RateLimit float64

	// MaxURLs is the maximum number of URLs to crawl (0 = unlimited).
	MaxURLs int

	// UserAgent is the user agent string.
	UserAgent string

	// Timeout for HTTP requests.
	Timeout time.Duration

	// UseRedis enables Redis-backed frontier for distributed crawling.
	UseRedis bool

	// RedisAddr is the Redis server address.
	RedisAddr string

	// FrontierCapacity is the capacity of the in-memory frontier.
	FrontierCapacity int

	// BloomExpectedItems is the expected number of items for the bloom filter.
	BloomExpectedItems uint

	// BloomFalsePositiveRate is the false positive rate for the bloom filter.
	BloomFalsePositiveRate float64
}

// DefaultOptions returns the default crawler options.
func DefaultOptions() Options {
	return Options{
		Workers:                10,
		RateLimit:              5.0,
		MaxURLs:                0,
		UserAgent:              "GoCrawler/1.0",
		Timeout:                30 * time.Second,
		UseRedis:               false,
		RedisAddr:              "localhost:6379",
		FrontierCapacity:       100000,
		BloomExpectedItems:     1000000,
		BloomFalsePositiveRate: 0.01,
	}
}

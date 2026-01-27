package frontier

import (
	"context"
	"time"
)

// Frontier represents a URL queue for crawling.
type Frontier interface {
	// Push adds a URL to the queue.
	Push(ctx context.Context, url string) error

	// Pop removes and returns a URL from the queue.
	// Blocks until a URL is available or context is cancelled.
	Pop(ctx context.Context) (string, error)

	// PopWithTimeout removes and returns a URL from the queue with a timeout.
	// Returns empty string and nil error if timeout expires with no URL.
	PopWithTimeout(ctx context.Context, timeout time.Duration) (string, error)

	// Size returns the current number of URLs in the queue.
	Size() int64

	// Close closes the frontier and releases resources.
	Close() error
}

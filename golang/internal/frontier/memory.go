package frontier

import (
	"context"
	"sync/atomic"
	"time"
)

// MemoryFrontier is an in-memory channel-based URL queue.
type MemoryFrontier struct {
	ch     chan string
	size   int64
	closed int32
}

// NewMemoryFrontier creates a new memory-based frontier with the given capacity.
func NewMemoryFrontier(capacity int) *MemoryFrontier {
	return &MemoryFrontier{
		ch: make(chan string, capacity),
	}
}

// Push adds a URL to the queue.
func (f *MemoryFrontier) Push(ctx context.Context, url string) error {
	if atomic.LoadInt32(&f.closed) == 1 {
		return context.Canceled
	}

	select {
	case f.ch <- url:
		atomic.AddInt64(&f.size, 1)
		return nil
	case <-ctx.Done():
		return ctx.Err()
	}
}

// Pop removes and returns a URL from the queue.
func (f *MemoryFrontier) Pop(ctx context.Context) (string, error) {
	select {
	case url, ok := <-f.ch:
		if !ok {
			return "", context.Canceled
		}
		atomic.AddInt64(&f.size, -1)
		return url, nil
	case <-ctx.Done():
		return "", ctx.Err()
	}
}

// PopWithTimeout removes and returns a URL with a timeout.
func (f *MemoryFrontier) PopWithTimeout(ctx context.Context, timeout time.Duration) (string, error) {
	ctx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()

	select {
	case url, ok := <-f.ch:
		if !ok {
			return "", context.Canceled
		}
		atomic.AddInt64(&f.size, -1)
		return url, nil
	case <-ctx.Done():
		if ctx.Err() == context.DeadlineExceeded {
			return "", nil // Timeout is not an error
		}
		return "", ctx.Err()
	}
}

// Size returns the current number of URLs in the queue.
func (f *MemoryFrontier) Size() int64 {
	return atomic.LoadInt64(&f.size)
}

// Close closes the frontier.
func (f *MemoryFrontier) Close() error {
	if atomic.CompareAndSwapInt32(&f.closed, 0, 1) {
		close(f.ch)
	}
	return nil
}

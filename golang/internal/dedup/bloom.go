package dedup

import (
	"sync"

	"github.com/bits-and-blooms/bloom/v3"
)

// BloomDedup is a thread-safe bloom filter based deduplicator.
type BloomDedup struct {
	filter *bloom.BloomFilter
	mu     sync.Mutex
	count  uint64
}

// NewBloomDedup creates a new bloom filter deduplicator.
// expectedItems is the expected number of items to be added.
// fpRate is the desired false positive rate (e.g., 0.01 for 1%).
func NewBloomDedup(expectedItems uint, fpRate float64) *BloomDedup {
	return &BloomDedup{
		filter: bloom.NewWithEstimates(expectedItems, fpRate),
	}
}

// SeenOrAdd checks if URL was seen and adds it if not.
// Returns true if the URL was already seen (or might have been due to false positive).
func (b *BloomDedup) SeenOrAdd(url string) bool {
	b.mu.Lock()
	defer b.mu.Unlock()

	if b.filter.TestString(url) {
		return true
	}

	b.filter.AddString(url)
	b.count++
	return false
}

// Seen checks if URL was seen without adding it.
func (b *BloomDedup) Seen(url string) bool {
	b.mu.Lock()
	defer b.mu.Unlock()
	return b.filter.TestString(url)
}

// Count returns the number of items added.
func (b *BloomDedup) Count() uint64 {
	b.mu.Lock()
	defer b.mu.Unlock()
	return b.count
}

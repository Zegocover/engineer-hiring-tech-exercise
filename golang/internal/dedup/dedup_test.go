package dedup

import (
	"fmt"
	"sync"
	"testing"
)

func TestBloomDedup_SeenOrAdd(t *testing.T) {
	dedup := NewBloomDedup(1000, 0.01)

	url1 := "https://example.com/page1"
	url2 := "https://example.com/page2"

	// First time seeing url1
	if dedup.SeenOrAdd(url1) {
		t.Error("expected false for first add of url1")
	}

	// Second time seeing url1
	if !dedup.SeenOrAdd(url1) {
		t.Error("expected true for second add of url1")
	}

	// First time seeing url2
	if dedup.SeenOrAdd(url2) {
		t.Error("expected false for first add of url2")
	}

	// Check count
	if dedup.Count() != 2 {
		t.Errorf("expected count 2, got %d", dedup.Count())
	}
}

func TestBloomDedup_Seen(t *testing.T) {
	dedup := NewBloomDedup(1000, 0.01)

	url := "https://example.com/page"

	// Not seen yet
	if dedup.Seen(url) {
		t.Error("expected false before adding")
	}

	dedup.SeenOrAdd(url)

	// Now seen
	if !dedup.Seen(url) {
		t.Error("expected true after adding")
	}
}

func TestBloomDedup_Concurrent(t *testing.T) {
	dedup := NewBloomDedup(10000, 0.001) // Lower FP rate for test

	var wg sync.WaitGroup
	numGoroutines := 100
	urlsPerGoroutine := 100

	wg.Add(numGoroutines)
	for i := 0; i < numGoroutines; i++ {
		go func(id int) {
			defer wg.Done()
			for j := 0; j < urlsPerGoroutine; j++ {
				url := fmt.Sprintf("https://example.com/page%d-%d", id, j)
				dedup.SeenOrAdd(url)
			}
		}(i)
	}

	wg.Wait()

	expectedCount := uint64(numGoroutines * urlsPerGoroutine)
	count := dedup.Count()
	// Allow for small variance due to bloom filter false positives
	// With 0.1% FP rate, we expect ~10 false positives out of 10000
	minCount := expectedCount - 50
	if count < minCount || count > expectedCount {
		t.Errorf("expected count near %d, got %d", expectedCount, count)
	}
}

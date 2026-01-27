package frontier

import (
	"context"
	"sync"
	"testing"
	"time"
)

func TestMemoryFrontier_PushPop(t *testing.T) {
	f := NewMemoryFrontier(100)
	defer f.Close()

	ctx := context.Background()

	urls := []string{
		"https://example.com/page1",
		"https://example.com/page2",
		"https://example.com/page3",
	}

	for _, url := range urls {
		if err := f.Push(ctx, url); err != nil {
			t.Fatalf("Push failed: %v", err)
		}
	}

	if f.Size() != 3 {
		t.Errorf("expected size 3, got %d", f.Size())
	}

	for _, expected := range urls {
		url, err := f.Pop(ctx)
		if err != nil {
			t.Fatalf("Pop failed: %v", err)
		}
		if url != expected {
			t.Errorf("got %q, want %q", url, expected)
		}
	}

	if f.Size() != 0 {
		t.Errorf("expected size 0, got %d", f.Size())
	}
}

func TestMemoryFrontier_PopWithTimeout(t *testing.T) {
	f := NewMemoryFrontier(100)
	defer f.Close()

	ctx := context.Background()

	// Test timeout with empty queue
	start := time.Now()
	url, err := f.PopWithTimeout(ctx, 100*time.Millisecond)
	elapsed := time.Since(start)

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if url != "" {
		t.Errorf("expected empty string, got %q", url)
	}
	if elapsed < 100*time.Millisecond {
		t.Errorf("timeout too fast: %v", elapsed)
	}

	// Test with URL available
	if err := f.Push(ctx, "https://example.com"); err != nil {
		t.Fatalf("Push failed: %v", err)
	}

	url, err = f.PopWithTimeout(ctx, time.Second)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if url != "https://example.com" {
		t.Errorf("got %q, want %q", url, "https://example.com")
	}
}

func TestMemoryFrontier_Concurrent(t *testing.T) {
	f := NewMemoryFrontier(1000)
	defer f.Close()

	ctx := context.Background()
	numProducers := 10
	numConsumers := 10
	urlsPerProducer := 100

	var wg sync.WaitGroup
	consumed := make(chan string, numProducers*urlsPerProducer)

	// Start producers
	wg.Add(numProducers)
	for i := 0; i < numProducers; i++ {
		go func(id int) {
			defer wg.Done()
			for j := 0; j < urlsPerProducer; j++ {
				url := "https://example.com/page"
				if err := f.Push(ctx, url); err != nil {
					return
				}
			}
		}(i)
	}

	// Start consumers
	var consumersWg sync.WaitGroup
	consumersWg.Add(numConsumers)
	stopConsumers := make(chan struct{})
	for i := 0; i < numConsumers; i++ {
		go func() {
			defer consumersWg.Done()
			for {
				select {
				case <-stopConsumers:
					return
				default:
					url, err := f.PopWithTimeout(ctx, 50*time.Millisecond)
					if err != nil {
						return
					}
					if url != "" {
						consumed <- url
					}
				}
			}
		}()
	}

	// Wait for producers to finish
	wg.Wait()

	// Wait for queue to drain
	for f.Size() > 0 {
		time.Sleep(10 * time.Millisecond)
	}

	close(stopConsumers)
	consumersWg.Wait()
	close(consumed)

	count := 0
	for range consumed {
		count++
	}

	expected := numProducers * urlsPerProducer
	if count != expected {
		t.Errorf("consumed %d URLs, expected %d", count, expected)
	}
}

func TestMemoryFrontier_ContextCancel(t *testing.T) {
	f := NewMemoryFrontier(100)
	defer f.Close()

	ctx, cancel := context.WithCancel(context.Background())

	// Cancel immediately
	cancel()

	// Pop should return context error
	_, err := f.Pop(ctx)
	if err != context.Canceled {
		t.Errorf("expected context.Canceled, got %v", err)
	}
}

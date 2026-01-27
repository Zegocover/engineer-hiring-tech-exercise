package fetcher

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

func TestHTTPFetcher_Fetch(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/":
			w.Header().Set("Content-Type", "text/html")
			w.Write([]byte("<html><body>Hello</body></html>"))
		case "/404":
			w.WriteHeader(http.StatusNotFound)
		case "/slow":
			time.Sleep(2 * time.Second)
			w.Write([]byte("slow"))
		default:
			w.WriteHeader(http.StatusNotFound)
		}
	}))
	defer server.Close()

	cfg := DefaultConfig()
	cfg.RateLimit = 100 // High rate for testing
	fetcher := NewHTTPFetcher(cfg)

	t.Run("successful fetch", func(t *testing.T) {
		result := fetcher.Fetch(context.Background(), server.URL+"/")

		if result.Error != nil {
			t.Fatalf("unexpected error: %v", result.Error)
		}
		if result.StatusCode != 200 {
			t.Errorf("expected status 200, got %d", result.StatusCode)
		}
		if string(result.Body) != "<html><body>Hello</body></html>" {
			t.Errorf("unexpected body: %s", result.Body)
		}
		if result.ContentType != "text/html" {
			t.Errorf("expected content-type text/html, got %s", result.ContentType)
		}
	})

	t.Run("404 response", func(t *testing.T) {
		result := fetcher.Fetch(context.Background(), server.URL+"/404")

		if result.Error != nil {
			t.Fatalf("unexpected error: %v", result.Error)
		}
		if result.StatusCode != 404 {
			t.Errorf("expected status 404, got %d", result.StatusCode)
		}
	})

	t.Run("context cancellation", func(t *testing.T) {
		ctx, cancel := context.WithCancel(context.Background())
		cancel()

		result := fetcher.Fetch(ctx, server.URL+"/slow")

		if result.Error == nil {
			t.Error("expected error for cancelled context")
		}
	})
}

func TestHTTPFetcher_UserAgent(t *testing.T) {
	var receivedUA string
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		receivedUA = r.Header.Get("User-Agent")
		w.Write([]byte("ok"))
	}))
	defer server.Close()

	cfg := DefaultConfig()
	cfg.UserAgent = "TestCrawler/1.0"
	cfg.RateLimit = 100
	fetcher := NewHTTPFetcher(cfg)

	fetcher.Fetch(context.Background(), server.URL)

	if receivedUA != "TestCrawler/1.0" {
		t.Errorf("expected user agent 'TestCrawler/1.0', got '%s'", receivedUA)
	}
}

func TestMockFetcher(t *testing.T) {
	mock := NewMockFetcher()
	mock.AddHTMLResponse("https://example.com", "<html></html>")

	result := mock.Fetch(context.Background(), "https://example.com")

	if result.StatusCode != 200 {
		t.Errorf("expected status 200, got %d", result.StatusCode)
	}
	if string(result.Body) != "<html></html>" {
		t.Errorf("unexpected body: %s", result.Body)
	}

	calls := mock.Calls()
	if len(calls) != 1 || calls[0] != "https://example.com" {
		t.Errorf("unexpected calls: %v", calls)
	}
}

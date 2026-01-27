package robots

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestChecker_IsAllowed(t *testing.T) {
	// Note: When a specific user-agent is matched, only those rules apply
	// So GoCrawler only sees Disallow: /blocked/, not the * rules
	robotsTxt := `
User-agent: GoCrawler
Disallow: /blocked/
Disallow: /private/
Crawl-delay: 2

User-agent: *
Disallow: /admin
`

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/robots.txt" {
			w.Write([]byte(robotsTxt))
		}
	}))
	defer server.Close()

	checker := NewChecker("GoCrawler")
	err := checker.Fetch(context.Background(), server.URL)
	if err != nil {
		t.Fatalf("Fetch failed: %v", err)
	}

	tests := []struct {
		path     string
		expected bool
	}{
		{server.URL + "/", true},
		{server.URL + "/page", true},
		{server.URL + "/blocked/", false},
		{server.URL + "/blocked/page", false},
		{server.URL + "/private/", false},
		{server.URL + "/admin", true}, // GoCrawler doesn't see * rules
	}

	for _, tt := range tests {
		t.Run(tt.path, func(t *testing.T) {
			result := checker.IsAllowed(tt.path)
			if result != tt.expected {
				t.Errorf("IsAllowed(%q) = %v, want %v", tt.path, result, tt.expected)
			}
		})
	}
}

func TestChecker_CrawlDelay(t *testing.T) {
	robotsTxt := `
User-agent: TestBot
Crawl-delay: 5
`

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte(robotsTxt))
	}))
	defer server.Close()

	checker := NewChecker("TestBot")
	err := checker.Fetch(context.Background(), server.URL)
	if err != nil {
		t.Fatalf("Fetch failed: %v", err)
	}

	delay := checker.CrawlDelay()
	if delay.Seconds() != 5 {
		t.Errorf("CrawlDelay() = %v, want 5s", delay)
	}
}

func TestChecker_NoRobotsTxt(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusNotFound)
	}))
	defer server.Close()

	checker := NewChecker("GoCrawler")
	err := checker.Fetch(context.Background(), server.URL)
	if err != nil {
		t.Fatalf("Fetch failed: %v", err)
	}

	// Should allow everything when no robots.txt
	if !checker.IsAllowed(server.URL + "/anything") {
		t.Error("expected all URLs to be allowed when no robots.txt")
	}
}

func TestChecker_NetworkError(t *testing.T) {
	checker := NewChecker("GoCrawler")

	// Use invalid URL that won't connect
	err := checker.Fetch(context.Background(), "http://localhost:99999")
	if err != nil {
		t.Fatalf("Fetch should not return error for network issues: %v", err)
	}

	// Should allow everything when can't fetch robots.txt
	if !checker.IsAllowed("http://localhost:99999/anything") {
		t.Error("expected all URLs to be allowed when can't fetch robots.txt")
	}
}

package fetcher

import (
	"context"
	"sync"
)

// MockFetcher is a mock fetcher for testing.
type MockFetcher struct {
	mu        sync.Mutex
	responses map[string]*Result
	calls     []string
}

// NewMockFetcher creates a new mock fetcher.
func NewMockFetcher() *MockFetcher {
	return &MockFetcher{
		responses: make(map[string]*Result),
	}
}

// AddResponse adds a mock response for a URL.
func (m *MockFetcher) AddResponse(url string, result *Result) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.responses[url] = result
}

// AddHTMLResponse adds a mock HTML response for a URL.
func (m *MockFetcher) AddHTMLResponse(url string, html string) {
	m.AddResponse(url, &Result{
		URL:         url,
		StatusCode:  200,
		Body:        []byte(html),
		ContentType: "text/html",
	})
}

// Fetch returns the mock response for the URL.
func (m *MockFetcher) Fetch(ctx context.Context, url string) *Result {
	m.mu.Lock()
	defer m.mu.Unlock()

	m.calls = append(m.calls, url)

	if result, ok := m.responses[url]; ok {
		return result
	}

	return &Result{
		URL:        url,
		StatusCode: 404,
	}
}

// Calls returns the list of URLs that were fetched.
func (m *MockFetcher) Calls() []string {
	m.mu.Lock()
	defer m.mu.Unlock()
	return append([]string{}, m.calls...)
}

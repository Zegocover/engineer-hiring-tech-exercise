package domain

import (
	"testing"
)

func TestNormalize(t *testing.T) {
	tests := []struct {
		name     string
		input    string
		expected string
	}{
		{"remove fragment", "https://example.com/page#section", "https://example.com/page"},
		{"remove trailing slash", "https://example.com/page/", "https://example.com/page"},
		{"keep root slash", "https://example.com/", "https://example.com/"},
		{"add root slash", "https://example.com", "https://example.com/"},
		{"keep query", "https://example.com/page?q=1", "https://example.com/page?q=1"},
		{"complex path", "https://example.com/a/b/c/", "https://example.com/a/b/c"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result, err := Normalize(tt.input)
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if result != tt.expected {
				t.Errorf("got %q, want %q", result, tt.expected)
			}
		})
	}
}

func TestResolveURL(t *testing.T) {
	tests := []struct {
		name     string
		base     string
		href     string
		expected string
	}{
		{"absolute URL", "https://example.com/page", "https://other.com/path", "https://other.com/path"},
		{"relative path", "https://example.com/page", "/other", "https://example.com/other"},
		{"relative no slash", "https://example.com/dir/page", "other", "https://example.com/dir/other"},
		{"parent dir", "https://example.com/a/b/c", "../d", "https://example.com/a/d"},
		{"fragment only", "https://example.com/page", "#section", "https://example.com/page"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result, err := ResolveURL(tt.base, tt.href)
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if result != tt.expected {
				t.Errorf("got %q, want %q", result, tt.expected)
			}
		})
	}
}

func TestIsSameDomain(t *testing.T) {
	tests := []struct {
		name     string
		base     string
		check    string
		expected bool
	}{
		{"same domain", "https://example.com/a", "https://example.com/b", true},
		{"different domain", "https://example.com/a", "https://other.com/b", false},
		{"subdomain different", "https://example.com/a", "https://www.example.com/b", false},
		{"case insensitive", "https://Example.COM/a", "https://example.com/b", true},
		{"different scheme same host", "http://example.com/a", "https://example.com/b", true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := IsSameDomain(tt.base, tt.check)
			if result != tt.expected {
				t.Errorf("got %v, want %v", result, tt.expected)
			}
		})
	}
}

func TestIsValidHTTP(t *testing.T) {
	tests := []struct {
		name     string
		input    string
		expected bool
	}{
		{"https", "https://example.com", true},
		{"http", "http://example.com", true},
		{"ftp", "ftp://example.com", false},
		{"mailto", "mailto:test@example.com", false},
		{"javascript", "javascript:void(0)", false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := IsValidHTTP(tt.input)
			if result != tt.expected {
				t.Errorf("got %v, want %v", result, tt.expected)
			}
		})
	}
}

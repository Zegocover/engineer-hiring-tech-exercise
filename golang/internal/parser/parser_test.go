package parser

import (
	"testing"
)

func TestParser_ExtractLinks(t *testing.T) {
	parser := NewParser()

	tests := []struct {
		name     string
		baseURL  string
		html     string
		expected []string
	}{
		{
			name:    "absolute links",
			baseURL: "https://example.com",
			html: `<html>
				<a href="https://example.com/page1">Page 1</a>
				<a href="https://other.com/page2">Page 2</a>
			</html>`,
			expected: []string{
				"https://example.com/page1",
				"https://other.com/page2",
			},
		},
		{
			name:    "relative links",
			baseURL: "https://example.com/dir/",
			html: `<html>
				<a href="/page1">Page 1</a>
				<a href="page2">Page 2</a>
				<a href="../other">Other</a>
			</html>`,
			expected: []string{
				"https://example.com/page1",
				"https://example.com/dir/page2",
				"https://example.com/other",
			},
		},
		{
			name:    "skip javascript and mailto",
			baseURL: "https://example.com",
			html: `<html>
				<a href="javascript:void(0)">JS</a>
				<a href="mailto:test@example.com">Email</a>
				<a href="tel:+1234567890">Phone</a>
				<a href="https://example.com/valid">Valid</a>
			</html>`,
			expected: []string{
				"https://example.com/valid",
			},
		},
		{
			name:    "skip fragment-only links",
			baseURL: "https://example.com/page",
			html: `<html>
				<a href="#section">Section</a>
				<a href="https://example.com/other#section">Other</a>
			</html>`,
			expected: []string{
				"https://example.com/other",
			},
		},
		{
			name:    "dedupe links",
			baseURL: "https://example.com",
			html: `<html>
				<a href="/page1">Link 1</a>
				<a href="/page1">Link 1 again</a>
				<a href="/page1/">Link 1 with slash</a>
			</html>`,
			expected: []string{
				"https://example.com/page1",
			},
		},
		{
			name:    "empty and missing href",
			baseURL: "https://example.com",
			html: `<html>
				<a href="">Empty</a>
				<a>No href</a>
				<a href="   ">Whitespace</a>
				<a href="/valid">Valid</a>
			</html>`,
			expected: []string{
				"https://example.com/valid",
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			links, err := parser.ExtractLinks(tt.baseURL, []byte(tt.html))
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}

			if len(links) != len(tt.expected) {
				t.Fatalf("got %d links, want %d: %v", len(links), len(tt.expected), links)
			}

			for i, link := range links {
				if link != tt.expected[i] {
					t.Errorf("link %d: got %q, want %q", i, link, tt.expected[i])
				}
			}
		})
	}
}

func TestParser_FilterSameDomain(t *testing.T) {
	parser := NewParser()

	baseURL := "https://example.com"
	links := []string{
		"https://example.com/page1",
		"https://other.com/page2",
		"https://example.com/page3",
		"https://www.example.com/page4",
	}

	filtered := parser.FilterSameDomain(baseURL, links)

	expected := []string{
		"https://example.com/page1",
		"https://example.com/page3",
	}

	if len(filtered) != len(expected) {
		t.Fatalf("got %d links, want %d", len(filtered), len(expected))
	}

	for i, link := range filtered {
		if link != expected[i] {
			t.Errorf("link %d: got %q, want %q", i, link, expected[i])
		}
	}
}

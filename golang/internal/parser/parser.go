package parser

import (
	"bytes"
	"strings"

	"github.com/PuerkitoBio/goquery"

	"webcrawler/internal/domain"
)

// Parser extracts links from HTML content.
type Parser struct{}

// NewParser creates a new HTML parser.
func NewParser() *Parser {
	return &Parser{}
}

// ExtractLinks extracts all valid links from HTML content.
// It resolves relative URLs against the base URL.
func (p *Parser) ExtractLinks(baseURL string, htmlContent []byte) ([]string, error) {
	doc, err := goquery.NewDocumentFromReader(bytes.NewReader(htmlContent))
	if err != nil {
		return nil, err
	}

	var links []string
	seen := make(map[string]bool)

	doc.Find("a[href]").Each(func(_ int, s *goquery.Selection) {
		href, exists := s.Attr("href")
		if !exists {
			return
		}

		// Skip empty, javascript, mailto, and fragment-only links
		href = strings.TrimSpace(href)
		if href == "" ||
			strings.HasPrefix(href, "javascript:") ||
			strings.HasPrefix(href, "mailto:") ||
			strings.HasPrefix(href, "tel:") ||
			strings.HasPrefix(href, "data:") ||
			(strings.HasPrefix(href, "#") && len(href) > 1) {
			return
		}

		// Resolve relative URL to absolute
		absoluteURL, err := domain.ResolveURL(baseURL, href)
		if err != nil {
			return
		}

		// Skip non-HTTP URLs
		if !domain.IsValidHTTP(absoluteURL) {
			return
		}

		// Dedupe within this page
		if seen[absoluteURL] {
			return
		}
		seen[absoluteURL] = true

		links = append(links, absoluteURL)
	})

	return links, nil
}

// FilterSameDomain filters links to only include those on the same domain.
func (p *Parser) FilterSameDomain(baseURL string, links []string) []string {
	var filtered []string
	for _, link := range links {
		if domain.IsSameDomain(baseURL, link) {
			filtered = append(filtered, link)
		}
	}
	return filtered
}

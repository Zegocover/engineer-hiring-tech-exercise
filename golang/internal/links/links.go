package links

import (
	"fmt"
	"net/url"
	"strings"

	"golang.org/x/net/html"
)

// Extract extracts href attribute values from anchor elements in buf.
// It returns the values as parsed from HTML, without resolving URLs, removing
// fragments, filtering schemes or hostnames, or deduplicating links.
//
// # Common href formats
//
// These examples assume the current page is https://example.com/blog/post,
// the seed hostname is example.com, and there is no HTML <base> override.
// The handling described below is the caller's responsibility.
//
//   - https://example.com/about: Absolute URL; crawl because the hostname matches.
//   - /about: Root-relative URL; resolves to https://example.com/about.
//   - about: Path-relative URL; resolves to https://example.com/blog/about.
//   - ../about: Parent-relative URL; resolves to https://example.com/about.
//   - //example.com/about: Inherits the current scheme; resolves to https://example.com/about.
//   - ?page=2: Keeps the current path and replaces the query; resolves to https://example.com/blog/post?page=2.
//   - #section: A fragment on the current page; remove the fragment before deduplication.
//   - /about#team: A fragment on another page; fetch https://example.com/about.
//   - "" (empty value): Resolves to the current page, which is usually already visited.
//   - mailto:hi@example.com: Email link; do not fetch.
//   - tel:+351123456789: Telephone link; do not fetch.
//   - javascript:void(0): JavaScript action; do not execute or fetch.
//   - data:...: Embedded data; do not fetch.
//   - https://other.com/page: External hostname; report the link without crawling it.
//   - https://sub.example.com/page: Subdomain with a different hostname; report without crawling it.
func Extract(base *url.URL, buf string) ([]*url.URL, error) {
	reader := strings.NewReader(buf)

	doc, err := html.Parse(reader)
	if err != nil {
		return nil, fmt.Errorf("parsing html: %w", err)
	}

	var hyperlinks []string
	for child := doc.FirstChild; child != nil; child = child.NextSibling {
		traversal(child, &hyperlinks)
	}

	var output []*url.URL
	for i := range hyperlinks {
		ref, err := url.Parse(hyperlinks[i])
		if err != nil {
			return nil, err
		}

		resolved := base.ResolveReference(ref)
		resolved.Fragment = ""
		resolved.RawFragment = ""

		// Keep HTTP(S) pages; drop mailto, tel, javascript, and data links.
		if resolved.Scheme != "http" && resolved.Scheme != "https" {
			continue
		}

		output = append(output, resolved)
	}

	return output, nil
}

func traversal(n *html.Node, res *[]string) {
	if n.Type == html.ElementNode && n.Data == "a" {
		for _, a := range n.Attr {
			if a.Key == "href" {
				*res = append(*res, a.Val)
			}
		}
	}

	for child := n.FirstChild; child != nil; child = child.NextSibling {
		traversal(child, res)
	}
}

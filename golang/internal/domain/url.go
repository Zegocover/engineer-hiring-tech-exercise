package domain

import (
	"net/url"
	"strings"
)

// Normalize cleans up a URL by removing fragments and trailing slashes.
func Normalize(rawURL string) (string, error) {
	u, err := url.Parse(rawURL)
	if err != nil {
		return "", err
	}

	u.Fragment = ""

	if u.Path != "/" && strings.HasSuffix(u.Path, "/") {
		u.Path = strings.TrimSuffix(u.Path, "/")
	}

	if u.Path == "" {
		u.Path = "/"
	}

	return u.String(), nil
}

// ResolveURL resolves a potentially relative URL against a base URL.
func ResolveURL(base, href string) (string, error) {
	baseURL, err := url.Parse(base)
	if err != nil {
		return "", err
	}

	refURL, err := url.Parse(href)
	if err != nil {
		return "", err
	}

	resolved := baseURL.ResolveReference(refURL)
	return Normalize(resolved.String())
}

// IsSameDomain checks if the given URL belongs to the same domain as the base.
// Uses exact host match (no subdomain matching).
func IsSameDomain(baseURL, checkURL string) bool {
	base, err := url.Parse(baseURL)
	if err != nil {
		return false
	}

	check, err := url.Parse(checkURL)
	if err != nil {
		return false
	}

	return strings.EqualFold(base.Host, check.Host)
}

// IsValidHTTP checks if a URL is a valid HTTP/HTTPS URL.
func IsValidHTTP(rawURL string) bool {
	u, err := url.Parse(rawURL)
	if err != nil {
		return false
	}
	return u.Scheme == "http" || u.Scheme == "https"
}

// GetHost extracts the host from a URL.
func GetHost(rawURL string) (string, error) {
	u, err := url.Parse(rawURL)
	if err != nil {
		return "", err
	}
	return u.Host, nil
}

// GetBaseURL returns the scheme and host portion of a URL.
func GetBaseURL(rawURL string) (string, error) {
	u, err := url.Parse(rawURL)
	if err != nil {
		return "", err
	}
	return u.Scheme + "://" + u.Host, nil
}

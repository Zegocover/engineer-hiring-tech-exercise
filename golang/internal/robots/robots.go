// Package robots fetches robots.txt and exposes its parsed policy.
package robots

import (
	"context"
	"errors"
	"fmt"
	"net/url"

	"github.com/temoto/robotstxt"

	"zego.com/engineer-hiring-tech-exercise/internal/client"
)

type Policy struct {
	rules *robotstxt.RobotsData
}

// Load fetches and parses an origin's robots.txt once.
// A missing file permits access; retrieval or parse failures deny access.
func Load(ctx context.Context, c *client.Client, seed *url.URL) (*Policy, error) {
	u := &url.URL{Scheme: seed.Scheme, Host: seed.Host, Path: "/robots.txt"}
	body, err := c.Request(ctx, u)
	if httpErr, ok := errors.AsType[*client.HTTPError](err); ok && httpErr.Code >= 400 && httpErr.Code < 500 {
		body = "" // not found, allow everything
	} else if err != nil {
		return nil, fmt.Errorf("loading robots.txt: %w", err)
	}
	rules, err := robotstxt.FromString(body)
	if err != nil {
		return &Policy{}, nil
	}
	return &Policy{rules: rules}, nil
}

// Allowed checks a URL against the crawler user-agent rules without making requests.
func (p *Policy) Allowed(u *url.URL) bool {
	return p.rules != nil && p.rules.TestAgent(u.RequestURI(), client.UserAgent)
}

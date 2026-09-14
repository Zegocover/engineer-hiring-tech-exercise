package crawler

import (
	"context"
	"fmt"
	"log/slog"
	"net/url"

	"zego.com/engineer-hiring-tech-exercise/internal/client"
	"zego.com/engineer-hiring-tech-exercise/internal/links"
	"zego.com/engineer-hiring-tech-exercise/internal/robots"
)

type Crawler struct {
	client *client.Client
}

func NewCrawler(client *client.Client) *Crawler {
	return &Crawler{client: client}
}

func (c *Crawler) Crawl(ctx context.Context, slogger *slog.Logger, seedUrl *url.URL) ([]string, error) {
	visited := make(map[string]struct{})

	policies, err := robots.Load(ctx, c.client, seedUrl)
	if err != nil {
		return nil, fmt.Errorf("loading robots rules: %w", err)
	}

	pendingUrls := NewUniqueQueue(seedUrl)

	for nextURL := pendingUrls.Next(); nextURL != nil; nextURL = pendingUrls.Next() {
		l := slogger.With(slog.String("url", nextURL.String()))

		l.Debug("Process url")

		if isDomainLink(seedUrl, nextURL) {
			if !policies.Allowed(nextURL) {
				visited[nextURL.String()] = struct{}{}
				continue
			}

			res, err := c.client.Request(ctx, nextURL)
			if err != nil {
				l.ErrorContext(ctx, "Failed to request page", "error", err)
			}

			links, err := links.Extract(nextURL, res)
			if err != nil {
				l.ErrorContext(ctx, "Failed to extract links", "error", err)
			}

			var countNew int
			for i := range links {
				if pendingUrls.Append(links[i]) {
					l.Debug("Enqueue next url", "url", links[i].String())
					countNew++
				}
			}

			l.Debug("Result of process url", "total_links", len(links), "new_links", countNew, "already_scheduled", len(links)-countNew)
		}

		visited[nextURL.String()] = struct{}{}
	}

	// Collect Results
	var result []string
	for s := range visited {
		result = append(result, s)
	}

	return result, nil
}

func isDomainLink(baseUrl *url.URL, link *url.URL) bool {
	return link.Hostname() == baseUrl.Hostname()
}

type UniqueQueue struct {
	store []*url.URL
	seen  map[string]struct{}
}

func NewUniqueQueue(u *url.URL) UniqueQueue {
	q := UniqueQueue{seen: make(map[string]struct{})}
	q.Append(u)
	return q
}

func (q *UniqueQueue) Append(u *url.URL) bool {
	key := u.String()
	if _, exists := q.seen[key]; exists {
		return false
	}
	q.seen[key] = struct{}{}
	q.store = append(q.store, u)
	return true
}

func (q *UniqueQueue) Next() *url.URL {
	if len(q.store) == 0 {
		return nil
	}

	next := q.store[0]
	q.store = q.store[1:]
	return next
}

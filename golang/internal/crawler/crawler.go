package crawler

import (
	"context"
	"fmt"
	"log/slog"
	"net/url"

	"zego.com/engineer-hiring-tech-exercise/internal/client"
	"zego.com/engineer-hiring-tech-exercise/internal/links"
)

type Crawler struct {
	client *client.Client
}

func NewCrawler(client *client.Client) *Crawler {
	return &Crawler{client: client}
}

func (c *Crawler) Crawl(ctx context.Context, slogger *slog.Logger, seedUrl *url.URL) ([]string, error) {
	visited := make(map[string]struct{})

	pendingUrls := NewQueue(seedUrl)

	for nextURL := pendingUrls.Next(); nextURL != nil; nextURL = pendingUrls.Next() {
		l := slogger.With(slog.String("url", nextURL.String()))

		l.Debug("Process url")

		if isDomainLink(seedUrl, nextURL) {
			res, err := c.client.Request(ctx, nextURL)
			if err != nil {
				//TODO: add retries or deadletter queue
				return nil, fmt.Errorf("client requesting %s: %w", nextURL, err)
			}

			links, err := links.Extract(nextURL, res)
			if err != nil {
				// TODO: deal with the error here
				return nil, fmt.Errorf("get all links: %w", err)
			}

			var countNew int
			for i := range links {
				if _, ok := visited[links[i].String()]; !ok {
					l.Debug("Enqueue next url", "url", links[i].String())
					pendingUrls.Append(links[i])
					countNew++
				}
			}

			l.Debug("Result of process url", "total_links", len(links), "new_links", countNew, "visted_links", len(links)-countNew)
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

type Queue struct {
	store []*url.URL
}

func NewQueue(u *url.URL) Queue {
	return Queue{store: []*url.URL{u}}
}

func (q *Queue) Append(u *url.URL) {
	q.store = append(q.store, u)
}

func (q *Queue) Next() *url.URL {
	if len(q.store) == 0 {
		return nil
	}

	next := q.store[0]
	q.store = q.store[1:]
	return next
}

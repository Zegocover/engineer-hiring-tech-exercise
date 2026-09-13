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

func (c *Crawler) Crawl(ctx context.Context, slogger *slog.Logger, seedUrl *url.URL) ([]*url.URL, error) {
	pendingUrls := NewQueue(seedUrl)

	var visited []*url.URL

	for nextURL := pendingUrls.Next(); nextURL != nil; nextURL = pendingUrls.Next() {
		slogger.Debug("Next url", "url", nextURL.String())

		res, err := c.client.Request(ctx, nextURL)
		if err != nil {
			//TODO: add to the list of not visited
			return nil, fmt.Errorf("client requesting %s: %w", nextURL, err)
		}

		links, err := links.Extract(nextURL, res)
		if err != nil {
			// TODO: deal with the error here
			return nil, fmt.Errorf("get all links: %w", err)
		}

		slogger.Debug("Got %d links", "url", len(links))

		visited = append(visited, links...)

		pendingUrls.Append(onlyDomainLinks(seedUrl, links))
	}

	return visited, nil
}

func onlyDomainLinks(baseUrl *url.URL, links []*url.URL) []*url.URL {
	var out []*url.URL
	for i := range links {
		if links[i].Hostname() == baseUrl.Hostname() {
			out = append(out, links[i])
		}
	}
	return out
}

type Queue struct {
	store []*url.URL
}

func NewQueue(u *url.URL) Queue {
	return Queue{store: []*url.URL{u}}
}

func (q *Queue) Append(u []*url.URL) {
	q.store = append(q.store, u...)
}

func (q *Queue) Next() *url.URL {
	if len(q.store) == 0 {
		return nil
	}

	next := q.store[0]
	q.store = q.store[1:]
	return next
}

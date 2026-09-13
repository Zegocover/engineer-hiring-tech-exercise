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

func (c *Crawler) Crawl(ctx context.Context, slogger *slog.Logger, seedUrl *url.URL) error {
	l := slogger.With("url", seedUrl)

	res, err := c.client.Request(ctx, seedUrl)
	if err != nil {
		return fmt.Errorf("client requesting %s: %w", seedUrl, err)
	}

	links, err := links.GetAll(seedUrl, res)
	if err != nil {
		return fmt.Errorf("get all links: %w", err)
	}

	for i := range links {
		l.Debug("Parsing links", "url", links[i].String())
	}

	return nil
}

package crawler

import (
	"context"
	"fmt"
	"log/slog"
	"net/url"
	"strings"

	"zego.com/engineer-hiring-tech-exercise/internal/client"
	"zego.com/engineer-hiring-tech-exercise/internal/links"
)

type Crawler struct {
	client *client.Client
}

func NewCrawler(client *client.Client) *Crawler {
	return &Crawler{client: client}
}

func (c *Crawler) Crawl(ctx context.Context, slogger *slog.Logger, seedUrl *url.URL) (*Report, error) {
	res, err := c.client.Request(ctx, seedUrl)
	if err != nil {
		return nil, fmt.Errorf("client requesting %s: %w", seedUrl, err)
	}

	links, err := links.GetAll(seedUrl, res)
	if err != nil {
		return nil, fmt.Errorf("get all links: %w", err)
	}

	report := onlyDomainLinks(seedUrl, links)

	return report, nil
}

type Report struct {
	Internal []*url.URL
	External []*url.URL
}

func onlyDomainLinks(baseUrl *url.URL, links []*url.URL) *Report {
	var report Report
	for i := range links {
		if strings.EqualFold(links[i].Hostname(), baseUrl.Hostname()) {
			report.Internal = append(report.Internal, links[i])
		} else {
			report.External = append(report.External, links[i])
		}
	}
	return &report
}

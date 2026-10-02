package crawler

import (
	"context"
	"fmt"
	"log/slog"
	"net/url"
	"sync"

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
	ctx, cancel := context.WithCancel(ctx)
	defer cancel()

	visited := make(map[string]struct{})

	policies, err := robots.Load(ctx, c.client, seedUrl)
	if err != nil {
		return nil, fmt.Errorf("loading robots rules: %w", err)
	}

	inputCh := make(chan *url.URL)
	resultCh := make(chan Result)

	var wg sync.WaitGroup
	for i := 0; i < 4; i++ {
		l := slogger.With("workerID", i)
		wg.Go(func() { c.worker(ctx, l, inputCh, resultCh) })
	}

	defer func() {
		cancel()
		close(inputCh)
		wg.Wait()
	}()

	queue := NewUniqueQueue(seedUrl)
	inProgress := 0

	for {
		// exited trap
		if err := ctx.Err(); err != nil {
			return c.collectRows(visited), nil
		}

		// exited
		if queue.Size() == 0 && inProgress == 0 {
			break
		}

		nextLink := queue.Peek()

		var linkCh chan<- *url.URL

		if nextLink != nil {
			if isDomainLink(seedUrl, nextLink) && policies.Allowed(nextLink) {
				linkCh = inputCh
			} else {
				visited[nextLink.String()] = struct{}{}
				queue.Next()
				continue
			}
		}

		select {
		case <-ctx.Done():
			return c.collectRows(visited), nil
		case linkCh <- nextLink:
			inProgress++
			queue.Next()
		case result := <-resultCh:
			inProgress--
			visited[result.URL.String()] = struct{}{}
			if result.Err != nil {
				slogger.Error("Something bad happen with crawling", "error", result.Err)
				continue
			}
			for i := range result.Links {
				if queue.Append(result.Links[i]) {
					slogger.DebugContext(ctx, "Enqueue next url", "url", result.Links[i].String())
				}
			}
		}
	}

	return c.collectRows(visited), nil
}

func (c *Crawler) collectRows(visited map[string]struct{}) []string {
	// Collect Results
	var result []string
	for s := range visited {
		result = append(result, s)
	}
	return result
}

// Result reports completion of a job, including failed requests.
type Result struct {
	URL   *url.URL
	Links []*url.URL
	Err   error
}

func (c *Crawler) worker(ctx context.Context, logger *slog.Logger, input <-chan *url.URL, output chan<- Result) {
	for {
		select {
		case <-ctx.Done():
			return

		case u, ok := <-input:
			if !ok {
				return
			}

			if ctx.Err() != nil {
				return
			}

			l := logger.With("url", u.String())
			l.Debug("Worker process url")

			result := Result{URL: u}

			body, err := c.client.Request(ctx, u)
			if err != nil {
				result.Err = fmt.Errorf("requesting page %s: %w", u, err)
				l.ErrorContext(ctx, "Failed to request page", "error", result.Err)
			} else {
				result.Links, err = links.Extract(u, body)
				if err != nil {
					result.Err = fmt.Errorf("extracting links from %s: %w", u, err)
					l.ErrorContext(ctx, "Failed to extract links", "error", result.Err)
				}
			}

			select {
			case <-ctx.Done():
				return
			case output <- result:
			}
		}
	}
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

func (q *UniqueQueue) Peek() *url.URL {
	if len(q.store) == 0 {
		return nil
	}
	return q.store[0]
}

func (q *UniqueQueue) Size() int {
	return len(q.store)
}

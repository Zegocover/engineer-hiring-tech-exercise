package client

import (
	"context"
	"fmt"
	"io"
	"net/http"
	"net/url"
)

type HTTPError struct {
	Code    int
	Message string
}

// Error implements [error].
func (h *HTTPError) Error() string {
	return fmt.Sprintf("HTTP %d: %s", h.Code, h.Message)
}

// TODO: add rate limiter
// TODO: add header agent
// TODO: add otel
type Client struct {
	client http.Client
}

func NewClient() *Client {
	return new(Client)
}

func (c *Client) Request(ctx context.Context, u *url.URL) (string, error) {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, u.String(), http.NoBody)
	if err != nil {
		return "", fmt.Errorf("creating HTTP request: %w", err)
	}

	res, err := c.client.Do(req)
	if err != nil {
		return "", fmt.Errorf("calling HTTP service: %w", err)
	}

	defer res.Body.Close()

	if res.StatusCode < http.StatusOK || res.StatusCode >= http.StatusMultipleChoices {
		body, err := io.ReadAll(res.Body)
		if err != nil {
			return "", fmt.Errorf("decoding response body: %w", err)
		}

		return "", &HTTPError{Code: res.StatusCode, Message: string(body)}
	}

	out, err := io.ReadAll(res.Body)
	if err != nil {
		return "", fmt.Errorf("reading HTTP response body: %w", err)
	}

	return string(out), nil
}

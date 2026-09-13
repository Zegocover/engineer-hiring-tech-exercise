package crawler

import (
	"log/slog"
	"net/http"
	"net/http/httptest"
	"net/url"
	"strings"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"zego.com/engineer-hiring-tech-exercise/internal/client"
)

func TestCrawl(t *testing.T) {
	tests := []struct {
		name         string
		givenBody    string
		status       int
		wantInternal []string
		wantExternal []string
		wantError    string
	}{
		{
			name: "HappyPath_MatchHost",
			givenBody: `<a href="https://{{host}}/absolute">Absolute</a>
				<a href="/root">Root relative</a>
				<a href="relative">Path relative</a>
				<a href="../parent">Parent relative</a>
				<a href="//{{host}}/scheme">Scheme relative</a>
				<a href="?page=2">Query</a>
				<a href="#team">Fragment</a>
				<a href="https://{{host}}/about#team">Absolute with fragment</a>
				<a href="https://example.com/external">External</a>
				<a href="mailto:hello@example.com">Email</a>`,
			wantInternal: []string{
				"https://{{host}}/absolute",
				"http://{{host}}/root",
				"http://{{host}}/blog/relative",
				"http://{{host}}/parent",
				"http://{{host}}/scheme",
				"http://{{host}}/blog/post?page=2",
				"http://{{host}}/blog/post",
				"https://{{host}}/about",
			},
			wantExternal: []string{"https://example.com/external"},
		},
		{
			name: "HappyPath_ReportExternalLinks",
			givenBody: `<a href="https://example.com/about">External</a>
				<a href="https://other.example.com/page">Another external host</a>`,
			wantExternal: []string{"https://example.com/about", "https://other.example.com/page"},
		},
		{
			name:         "HappyPath_ReportSubdomainLinks",
			givenBody:    `<a href="https://sub.{{host}}/about">Subdomain</a>`,
			wantExternal: []string{"https://sub.{{host}}/about"},
		},
		{
			name:      "HappyPath_NoLinks",
			givenBody: `<p>No links</p>`,
		},
		{
			name:      "UnhappyPath_HTTPFailure",
			givenBody: "unavailable", status: http.StatusServiceUnavailable,
			wantError: "client requesting",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			givenBody := tt.givenBody
			server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
				if tt.status != 0 {
					w.WriteHeader(tt.status)
				}
				_, _ = w.Write([]byte(givenBody))
			}))

			t.Cleanup(server.Close)

			seed, err := url.Parse(server.URL + "/blog/post")
			require.NoError(t, err)

			givenBody = strings.ReplaceAll(givenBody, "{{host}}", seed.Host)

			got, err := NewCrawler(client.NewClient()).Crawl(t.Context(), slog.Default(), seed)
			if tt.wantError != "" {
				require.ErrorContains(t, err, tt.wantError)
				var httpErr *client.HTTPError
				require.ErrorAs(t, err, &httpErr)
				assert.Equal(t, tt.status, httpErr.Code)
				assert.Nil(t, got)
				return
			}
			require.NoError(t, err)

			parseURLs := func(rawURLs []string) []*url.URL {
				var urls []*url.URL
				for _, rawURL := range rawURLs {
					u, err := url.Parse(strings.ReplaceAll(rawURL, "{{host}}", seed.Host))
					require.NoError(t, err)
					urls = append(urls, u)
				}
				return urls
			}
			assert.Equal(t, &Report{Internal: parseURLs(tt.wantInternal), External: parseURLs(tt.wantExternal)}, got)
		})
	}
}

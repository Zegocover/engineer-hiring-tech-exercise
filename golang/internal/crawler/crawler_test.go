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
		name      string
		handler   http.HandlerFunc
		wantValue []*url.URL
		wantError string
	}{
		{
			name: "HappyPath_MatchHost",
			handler: func(w http.ResponseWriter, r *http.Request) {
				if r.URL.Path != "/blog/post" || r.URL.RawQuery != "" {
					return
				}
				body := `<a href="http://{{host}}/absolute">Absolute</a>
				<a href="/root">Root relative</a>
				<a href="relative">Path relative</a>
				<a href="../parent">Parent relative</a>
				<a href="//{{host}}/scheme">Scheme relative</a>
				<a href="?page=2">Query</a>
				<a href="/fragment#team">Fragment</a>
				<a href="http://{{host}}/about#team">Absolute with fragment</a>
				<a href="https://example.com/external">External</a>
				<a href="mailto:hello@example.com">Email</a>`
				_, _ = w.Write([]byte(strings.ReplaceAll(body, "{{host}}", r.Host)))
			},
			wantValue: []*url.URL{
				mustParseURL(t, "http://fixture.test/absolute"),
				mustParseURL(t, "http://fixture.test/root"),
				mustParseURL(t, "http://fixture.test/blog/relative"),
				mustParseURL(t, "http://fixture.test/parent"),
				mustParseURL(t, "http://fixture.test/scheme"),
				mustParseURL(t, "http://fixture.test/blog/post?page=2"),
				mustParseURL(t, "http://fixture.test/fragment"),
				mustParseURL(t, "http://fixture.test/about"),
				mustParseURL(t, "https://example.com/external"),
			},
		},
		{
			name: "HappyPath_Nested",
			handler: func(w http.ResponseWriter, r *http.Request) {
				var body string
				switch r.URL.Path {
				case "/blog/post":
					body = `<a href="/docs/start">Start</a><a href="/about">About</a>`
				case "/docs/start":
					body = `<a href="guides/setup">Setup guide</a>`
				case "/about":
					body = `<p>About us</p>`
				case "/docs/guides/setup":
					body = `<a href="../reference#api">API reference</a>`
				case "/docs/reference":
					body = `<a href="https://example.com/reference">External reference</a>`
				default:
					http.NotFound(w, r)
					return
				}
				_, _ = w.Write([]byte(body))
			},
			wantValue: []*url.URL{
				mustParseURL(t, "http://fixture.test/docs/start"),
				mustParseURL(t, "http://fixture.test/about"),
				mustParseURL(t, "http://fixture.test/docs/guides/setup"),
				mustParseURL(t, "http://fixture.test/docs/reference"),
				mustParseURL(t, "https://example.com/reference"),
			},
		},
		{
			name: "HappyPath_Subdomain_Link",
			handler: func(w http.ResponseWriter, r *http.Request) {
				body := `<a href="https://sub.{{host}}/about">Subdomain</a>`
				_, _ = w.Write([]byte(strings.ReplaceAll(body, "{{host}}", r.Host)))
			},
			wantValue: []*url.URL{mustParseURL(t, "https://sub.fixture.test/about")},
		},
		{
			name: "HappyPath_NoLinks",
			handler: func(w http.ResponseWriter, r *http.Request) {
				body := `<p>No links</p>`
				_, _ = w.Write([]byte(strings.ReplaceAll(body, "{{host}}", r.Host)))
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			server := httptest.NewServer(tt.handler)

			t.Cleanup(server.Close)

			seed, err := url.Parse(server.URL + "/blog/post")
			require.NoError(t, err)

			wantValue := replaceFixtureHost(tt.wantValue, seed.Host)

			got, err := NewCrawler(client.NewClient()).Crawl(t.Context(), slog.Default(), seed)
			require.NoError(t, err)

			assert.Equal(t, wantValue, got)
		})
	}
}

func replaceFixtureHost(urls []*url.URL, host string) []*url.URL {
	var result []*url.URL
	for i := range urls {
		u := *urls[i]
		u.Host = strings.ReplaceAll(u.Host, "fixture.test", host)
		result = append(result, &u)
	}
	return result
}

func mustParseURL(t *testing.T, rawURL string) *url.URL {
	t.Helper()
	u, err := url.Parse(rawURL)
	require.NoError(t, err)
	return u
}

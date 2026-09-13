package crawler

import (
	"context"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"net/url"
	"slices"
	"strings"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"zego.com/engineer-hiring-tech-exercise/internal/client"
)

func TestCrawl(t *testing.T) {
	tests := []struct {
		name      string
		handler   http.HandlerFunc
		wantValue []string
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
			wantValue: []string{
				"http://fixture.test/blog/post",
				"http://fixture.test/absolute",
				"http://fixture.test/root",
				"http://fixture.test/blog/relative",
				"http://fixture.test/parent",
				"http://fixture.test/scheme",
				"http://fixture.test/blog/post?page=2",
				"http://fixture.test/fragment",
				"http://fixture.test/about",
				"https://example.com/external",
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
			wantValue: []string{
				"http://fixture.test/blog/post",
				"http://fixture.test/docs/start",
				"http://fixture.test/about",
				"http://fixture.test/docs/guides/setup",
				"http://fixture.test/docs/reference",
				"https://example.com/reference",
			},
		},
		{
			name: "HappyPath_Subdomain_Link",
			handler: func(w http.ResponseWriter, r *http.Request) {
				body := `<a href="https://sub.{{host}}/about">Subdomain</a>`
				_, _ = w.Write([]byte(strings.ReplaceAll(body, "{{host}}", r.Host)))
			},
			wantValue: []string{
				"http://fixture.test/blog/post",
				"https://sub.fixture.test/about",
			},
		},
		{
			name: "HappyPath_CircularDependency",
			handler: func(w http.ResponseWriter, r *http.Request) {
				switch r.URL.Path {
				case "/blog/post":
					_, _ = w.Write([]byte(`<a href="/about">About</a>`))
				case "/about":
					_, _ = w.Write([]byte(`<a href="/blog/post">Back to post</a>`))
				default:
					http.NotFound(w, r)
				}
			},
			wantValue: []string{
				"http://fixture.test/blog/post",
				"http://fixture.test/about",
			},
		},
		{
			name: "HappyPath_NoLinks",
			handler: func(w http.ResponseWriter, r *http.Request) {
				body := `<p>No links</p>`
				_, _ = w.Write([]byte(strings.ReplaceAll(body, "{{host}}", r.Host)))
			},
			wantValue: []string{
				"http://fixture.test/blog/post",
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			ctx, cancel := context.WithTimeout(t.Context(), 2*time.Second)
			defer cancel()
			server := httptest.NewServer(tt.handler)

			t.Cleanup(server.Close)

			seed, err := url.Parse(server.URL + "/blog/post")
			require.NoError(t, err)

			wantValue := replaceFixtureHost(tt.wantValue, seed.Host)

			gotValue, gotErr := NewCrawler(client.NewClient()).Crawl(ctx, slog.Default(), seed)
			require.NoError(t, gotErr)

			slices.Sort(wantValue)
			slices.Sort(gotValue)
			assert.Equal(t, wantValue, gotValue)
		})
	}
}

func replaceFixtureHost(urls []string, host string) []string {
	var result []string
	for i := range urls {
		result = append(result, strings.ReplaceAll(urls[i], "fixture.test", host))
	}
	return result
}

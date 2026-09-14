package main

import (
	"bytes"
	"context"
	"io"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"os"
	"slices"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestRun(t *testing.T) {
	tests := []struct {
		name        string
		folder      string
		seedUrl     string
		wanted      string
		wantError   string
		checkRobots bool
	}{
		{
			name:        "HappyPath_Robots",
			seedUrl:     "/",
			folder:      "testdata/robots/site",
			wanted:      "testdata/robots/crawl_output.txt",
			checkRobots: true,
		},
		{
			name:    "HappyPath_Base",
			seedUrl: "/",
			folder:  "testdata/base/site",
			wanted:  "testdata/base/crawl_output.txt",
		},
		{
			name:    "HappyPath_CircularDependency",
			seedUrl: "/start.html",
			folder:  "testdata/cycle/site",
			wanted:  "testdata/cycle/crawl_output.txt",
		},
		{
			name:    "HappyPath_Full",
			seedUrl: "/",
			folder:  "testdata/full/site",
			wanted:  "testdata/full/crawl_output.txt",
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			// given
			ctx, cancel := context.WithTimeout(t.Context(), 10*time.Second)
			defer cancel()

			var mu sync.Mutex
			requests := make(map[string]int)
			files := http.FileServer(http.Dir(tt.folder))
			server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				mu.Lock()
				requests[r.URL.Path]++
				mu.Unlock()
				files.ServeHTTP(w, r)
			}))
			t.Cleanup(server.Close)

			var output bytes.Buffer
			logger := slog.New(slog.NewTextHandler(io.Discard, nil))

			// when
			err := Run(ctx, logger, []string{server.URL + tt.seedUrl}, &output)
			if tt.wantError != "" {
				require.ErrorContains(t, err, tt.wantError)
				return
			}

			// then
			require.NoError(t, err)
			if tt.checkRobots {
				mu.Lock()
				assert.Equal(t, 1, requests["/robots.txt"])
				assert.Equal(t, 1, requests["/public.html"])
				assert.Zero(t, requests["/private.html"])
				mu.Unlock()
			}
			fixture, err := os.ReadFile(tt.wanted)
			require.NoError(t, err)

			wanted := strings.ReplaceAll(string(fixture), "{{baseURL}}", server.URL)
			wantURLs := strings.Fields(wanted)
			gotURLs := strings.Fields(output.String())

			slices.Sort(wantURLs)
			slices.Sort(gotURLs)
			assert.Equal(t, wantURLs, gotURLs)
		})
	}
}

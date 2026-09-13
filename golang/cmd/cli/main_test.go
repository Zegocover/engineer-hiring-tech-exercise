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
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestRun(t *testing.T) {
	tests := []struct {
		name      string
		folder    string
		seedUrl   string
		wanted    string
		wantError string
	}{
		{
			name:    "HappyPath_Base",
			seedUrl: "/index.html",
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
			seedUrl: "/index.html",
			folder:  "testdata/full/site",
			wanted:  "testdata/full/crawl_output.txt",
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			ctx, cancel := context.WithTimeout(t.Context(), 10*time.Second)
			defer cancel()

			server := httptest.NewServer(http.FileServer(http.Dir(tt.folder)))
			t.Cleanup(server.Close)

			var output bytes.Buffer
			logger := slog.New(slog.NewTextHandler(io.Discard, nil))

			err := Run(ctx, logger, []string{server.URL + tt.seedUrl}, &output)
			if tt.wantError != "" {
				require.ErrorContains(t, err, tt.wantError)
				return
			}

			require.NoError(t, err)

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

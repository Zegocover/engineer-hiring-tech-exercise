package crawler

import (
	"bytes"
	"context"
	"log"
	"net/http"
	"net/http/httptest"
	"reflect"
	"sort"
	"strings"
	"testing"

	"github.com/rijude/single-domain-crawler/go/internal/logging"
)

// TestNormalizeURL verifies URL validation and fragment removal.
func TestNormalizeURL(t *testing.T) {
	tests := []struct {
		name    string
		input   string
		want    string
		wantErr bool
	}{
		{name: "removes fragment", input: "https://example.com/path#section", want: "https://example.com/path"},
		{name: "rejects relative", input: "/path", wantErr: true},
		{name: "rejects non HTTP", input: "ftp://example.com/file", wantErr: true},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			got, err := normalizeURL(test.input)
			if (err != nil) != test.wantErr {
				t.Fatalf("normalizeURL() error = %v, wantErr %v", err, test.wantErr)
			}
			if err == nil && got.String() != test.want {
				t.Fatalf("normalizeURL() = %q, want %q", got, test.want)
			}
		})
	}
}

// TestCrawlExtractsOnlySameHostLinks verifies crawl boundaries and deduplication.
func TestCrawlExtractsOnlySameHostLinks(t *testing.T) {
	var serverURL string
	server := httptest.NewServer(http.HandlerFunc(func(response http.ResponseWriter, request *http.Request) {
		response.Header().Set("Content-Type", "text/html; charset=utf-8")
		switch request.URL.Path {
		case "/":
			response.Write([]byte(`<a href="/one#part">one</a><a href="/one">duplicate</a><a href="/two?x=1">two</a><a href="https://outside.example/path">external</a><a href="mailto:test@example.com">mail</a>`))
		case "/one":
			response.Write([]byte(`<a href="/">home</a>`))
		case "/two":
			response.Write([]byte(`<p>done</p>`))
		}
	}))
	defer server.Close()
	serverURL = server.URL

	got, err := New().Crawl(context.Background(), serverURL+"/", 2)
	if err != nil {
		t.Fatalf("Crawl() error = %v", err)
	}
	want := []string{serverURL + "/", serverURL + "/one", serverURL + "/two?x=1"}
	sort.Strings(got)
	sort.Strings(want)
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("Crawl() = %v, want %v", got, want)
	}
}

// TestCrawlRetriesTransientFailures verifies that transient HTTP failures are retried.
func TestCrawlRetriesTransientFailures(t *testing.T) {
	attempts := 0
	server := httptest.NewServer(http.HandlerFunc(func(response http.ResponseWriter, request *http.Request) {
		attempts++
		if attempts < maxFetchAttempts {
			response.WriteHeader(http.StatusServiceUnavailable)
			return
		}
		response.Header().Set("Content-Type", "text/html; charset=utf-8")
		response.WriteHeader(http.StatusOK)
	}))
	defer server.Close()

	got, err := New().Crawl(context.Background(), server.URL, 1)
	if err != nil {
		t.Fatalf("Crawl() error = %v", err)
	}
	if attempts != maxFetchAttempts {
		t.Fatalf("fetch attempts = %d, want %d", attempts, maxFetchAttempts)
	}
	if !reflect.DeepEqual(got, []string{server.URL}) {
		t.Fatalf("Crawl() URLs = %v, want %v", got, []string{server.URL})
	}
}

// TestCrawlReturnsSeedFailure verifies that a seed fetch error is returned.
func TestCrawlReturnsSeedFailure(t *testing.T) {
	server := httptest.NewServer(http.NotFoundHandler())
	defer server.Close()

	got, err := New().Crawl(context.Background(), server.URL, 1)
	if err == nil || !strings.Contains(err.Error(), "unexpected HTTP status") {
		t.Fatalf("Crawl() error = %v, want seed HTTP error", err)
	}
	if !reflect.DeepEqual(got, []string{server.URL}) {
		t.Fatalf("Crawl() URLs = %v, want %v", got, []string{server.URL})
	}
}

// TestCrawlRejectsInvalidWorkers verifies that zero workers are rejected.
func TestCrawlRejectsInvalidWorkers(t *testing.T) {
	if _, err := New().Crawl(context.Background(), "https://example.com", 0); err == nil {
		t.Fatal("Crawl() accepted zero workers")
	}
}

// TestParseLogLevel verifies supported and unsupported log-level names.
func TestParseLogLevel(t *testing.T) {
	for _, test := range []struct {
		input string
		want  logging.LogLevel
	}{
		{input: "error", want: logging.ErrorLevel},
		{input: "INFO", want: logging.InfoLevel},
		{input: " debug ", want: logging.DebugLevel},
	} {
		got, err := logging.ParseLogLevel(test.input)
		if err != nil || got != test.want {
			t.Fatalf("ParseLogLevel(%q) = %v, %v; want %v, nil", test.input, got, err, test.want)
		}
	}
	if _, err := logging.ParseLogLevel("trace"); err == nil {
		t.Fatal("ParseLogLevel accepted an invalid level")
	}
}

// TestLoggerFiltersLevels verifies that messages below the configured level are filtered.
func TestLoggerFiltersLevels(t *testing.T) {
	var output bytes.Buffer
	logger := logging.NewLogger(log.New(&output, "", 0), logging.InfoLevel)
	logger.Debugf("hidden")
	logger.Infof("visible")
	logger.Errorf("also visible")
	if strings.Contains(output.String(), "hidden") || !strings.Contains(output.String(), "INFO visible") || !strings.Contains(output.String(), "ERROR also visible") {
		t.Fatalf("unexpected log output: %q", output.String())
	}
}

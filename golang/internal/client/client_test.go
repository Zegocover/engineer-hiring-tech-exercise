package client

import (
	"net/http"
	"net/http/httptest"
	"net/url"
	"sync/atomic"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestClient_Request(t *testing.T) {
	tests := []struct {
		name      string
		handler   http.HandlerFunc
		wantValue string
		wantErr   error
	}{
		{
			name: "HappyPath",
			handler: func(w http.ResponseWriter, r *http.Request) {
				_, _ = w.Write([]byte(`<html><body><a href="/about">About</a></body></html>`))
			},
			wantValue: `<html><body><a href="/about">About</a></body></html>`,
		},
		{
			name: "HappyPath_PlainTextResponseBody",
			handler: func(w http.ResponseWriter, _ *http.Request) {
				_, _ = w.Write([]byte("plain text"))
			},
			wantValue: "plain text",
		},
		{
			name: "UnhappyPath_BadRequest",
			handler: func(w http.ResponseWriter, _ *http.Request) {
				w.WriteHeader(http.StatusBadRequest)
				_, _ = w.Write([]byte(`<html><body>Bad Request</body></html>`))
			},
			wantErr: &HTTPError{
				Code:    http.StatusBadRequest,
				Message: `<html><body>Bad Request</body></html>`,
			},
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			server := httptest.NewServer(tt.handler)
			t.Cleanup(server.Close)

			client := NewClient()

			serverURL, err := url.Parse(server.URL)
			assert.NoError(t, err)

			got, err := client.Request(t.Context(), serverURL)

			if tt.wantErr != nil {
				assert.ErrorContains(t, err, tt.wantErr.Error())
				assert.Empty(t, got)
				return
			}

			assert.NoError(t, err)
			assert.Equal(t, tt.wantValue, got)
		})
	}
}

func TestClientRejectsRedirects(t *testing.T) {
	for _, code := range []int{http.StatusMovedPermanently, http.StatusFound, http.StatusSeeOther, http.StatusTemporaryRedirect, http.StatusPermanentRedirect} {
		t.Run(http.StatusText(code), func(t *testing.T) {
			var fetched atomic.Int32
			server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				if r.URL.Path == "/target" {
					fetched.Add(1)
					return
				}
				http.Redirect(w, r, "/target", code)
			}))
			defer server.Close()
			u, err := url.Parse(server.URL)
			require.NoError(t, err)
			body, err := NewClient().Request(t.Context(), u)
			var httpErr *HTTPError
			require.ErrorAs(t, err, &httpErr)
			require.Equal(t, code, httpErr.Code)
			require.Empty(t, body)
			require.Zero(t, fetched.Load())
		})
	}
}

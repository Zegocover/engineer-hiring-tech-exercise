package client

import (
	"net/http"
	"net/http/httptest"
	"net/url"
	"testing"

	"github.com/stretchr/testify/assert"
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

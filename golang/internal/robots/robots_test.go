package robots

import (
	"net/http"
	"net/http/httptest"
	"net/url"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"zego.com/engineer-hiring-tech-exercise/internal/client"
)

func TestAllowed(t *testing.T) {
	tests := []struct {
		name   string
		body   string
		status int
		path   string
		want   bool
	}{

		{
			name:   "CrawlerSpecificRules",
			body:   "User-agent: *\nDisallow: /\n\nUser-agent: ExerciseCrawler\nDisallow: /private",
			status: http.StatusOK,
			path:   "/public",
			want:   true,
		},
		{
			name:   "AllowException",
			body:   "User-agent: *\nDisallow: /private\nAllow: /private/public",
			status: http.StatusOK,
			path:   "/private/public",
			want:   true,
		},
		{
			name:   "Wildcard",
			body:   "User-agent: *\nDisallow: /*.pdf$",
			status: http.StatusOK,
			path:   "/file.pdf",
			want:   false,
		},
		{
			name:   "HappyPath_NotFound",
			status: http.StatusNotFound,
			path:   "/anything",
			want:   true,
		},
		{
			name:   "HappyPath_Allowed",
			body:   "User-agent: *\nDisallow: /private",
			status: http.StatusOK,
			path:   "/public",
			want:   true,
		},
		{
			name:   "HappyPath_Disallowed",
			body:   "User-agent: *\nDisallow: /private",
			status: http.StatusOK,
			path:   "/private/page",
			want:   false,
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				assert.Equal(t, "/robots.txt", r.URL.Path)
				assert.Equal(t, "ExerciseCrawler/1.0", r.UserAgent())
				w.WriteHeader(tt.status)
				_, _ = w.Write([]byte(tt.body))
			}))
			t.Cleanup(server.Close)

			u, err := url.Parse(server.URL + tt.path)
			require.NoError(t, err)

			policy, err := Load(t.Context(), client.NewClient(), u)
			require.NoError(t, err)
			require.NotNil(t, policy)
			assert.Equal(t, tt.want, policy.Allowed(u))
		})
	}
}

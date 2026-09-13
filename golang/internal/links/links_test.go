package links

import (
	"net/url"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestClient_Traversal(t *testing.T) {
	tests := []struct {
		name      string
		input     string
		wantValue []*url.URL
	}{
		{
			name:      "HappyPath_Absolute",
			input:     `<html><body><a href="https://example.com/about">About</a></body></html>`,
			wantValue: []*url.URL{mustParseURL(t, "https://example.com/about")},
		},
		{
			name:      "HappyPath_RootRelative",
			input:     `<html><body><a href="/about">About</a></body></html>`,
			wantValue: []*url.URL{mustParseURL(t, "https://example.com/about")},
		},
		{
			name:      "HappyPath_PathRelative",
			input:     `<html><body><a href="about">About</a></body></html>`,
			wantValue: []*url.URL{mustParseURL(t, "https://example.com/about")},
		},
		{
			name:      "HappyPath_Fragment",
			input:     `<html><body><a href="/about#team">About</a></body></html>`,
			wantValue: []*url.URL{mustParseURL(t, "https://example.com/about")},
		},
		{
			name:      "HappyPath_InheritsCurrentscheme",
			input:     `<html><body><a href="//example.com/about">//example.com/about</a></body></html>`,
			wantValue: []*url.URL{mustParseURL(t, "https://example.com/about")},
		},
		{
			name:      "HappyPath_Exclude_Mailto",
			input:     `<html><body><a href="mailto:hi@example.com">//example.com/about</a></body></html>`,
			wantValue: nil,
		},
		{
			name:      "HappyPath_Exclude_Javascript",
			input:     `<html><body><a href="javascript:void(0)">//example.com/about</a></body></html>`,
			wantValue: nil,
		},
		{
			name:      "HappyPath_Exclude_Tel",
			input:     `<html><body><a href="tel:+351123456789">//example.com/about</a></body></html>`,
			wantValue: nil,
		},
		{
			name:      "HappyPath_Exclude_Data",
			input:     `<html><body><a href="data:text/plain,hello">//example.com/about</a></body></html>`,
			wantValue: nil,
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			base := mustParseURL(t, "https://example.com")

			gotValue, gotErr := GetAll(base, tt.input)
			require.NoError(t, gotErr)

			assert.Equal(t, tt.wantValue, gotValue)
		})
	}
}

func mustParseURL(t *testing.T, rawURL string) *url.URL {
	t.Helper()
	u, err := url.Parse(rawURL)
	require.NoError(t, err)
	return u
}

// ----- text chunking tests @ backend/internal/ingest/chunk_test.go -----
package ingest

import (
	"strings"
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestChunkTextBasic(t *testing.T) {
	text := "Sentence one. Sentence two. Sentence three. Sentence four. Sentence five. Sentence six. Sentence seven. Sentence eight. Sentence nine. Sentence ten."
	chunks := ChunkText(text, 5)
	assert.Greater(t, len(chunks), 0)

	for _, chunk := range chunks {
		assert.NotEmpty(t, strings.TrimSpace(chunk))
	}
}

func TestChunkTextSingleSentence(t *testing.T) {
	text := "Just one sentence here."
	chunks := ChunkText(text, 5)
	assert.Len(t, chunks, 1)
}

func TestChunkTextEmpty(t *testing.T) {
	chunks := ChunkText("", 5)
	assert.Empty(t, chunks)
}

func TestChunkTextCustomSize(t *testing.T) {
	text := "A. B. C. D. E. F. G."
	chunks := ChunkText(text, 3)
	assert.Greater(t, len(chunks), 0)
}

func TestNormalizeURL(t *testing.T) {
	tests := []struct {
		input    string
		expected string
	}{
		{"https://example.com/path/", "https://example.com/path"},
		{"https://example.com/", "https://example.com/"},
		{"https://example.com", "https://example.com/"},
		{"https://example.com/path?a=1", "https://example.com/path"},
	}
	for _, tt := range tests {
		result := NormalizeURL(tt.input)
		assert.Equal(t, tt.expected, result)
	}
}

func TestExtractInternalLinks(t *testing.T) {
	html := `<a href="/page1">link</a><a href="https://example.com/page2">link2</a><a href="https://other.com/page">ext</a>`
	links := ExtractInternalLinks(html, "https://example.com")
	assert.Len(t, links, 2)
}

func TestBuildLinkGraphSimple(t *testing.T) {
	pages := PageMap{
		"https://a.com": {OutboundLinks: []string{"https://b.com"}},
		"https://b.com": {OutboundLinks: []string{}},
	}
	graph := BuildLinkGraph(pages)
	assert.Equal(t, 0, graph[NormalizeURL("https://a.com")])
	assert.Equal(t, 1, graph[NormalizeURL("https://b.com")])
}

func TestBuildLinkGraphSelfLinkIgnored(t *testing.T) {
	pages := PageMap{
		"https://a.com": {OutboundLinks: []string{"https://a.com"}},
	}
	graph := BuildLinkGraph(pages)
	assert.Equal(t, 0, graph[NormalizeURL("https://a.com")])
}

func TestBuildLinkGraphExternalIgnored(t *testing.T) {
	pages := PageMap{
		"https://a.com": {OutboundLinks: []string{"https://other.com/page"}},
	}
	graph := BuildLinkGraph(pages)
	assert.Equal(t, 0, graph[NormalizeURL("https://a.com")])
}

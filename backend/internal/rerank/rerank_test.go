// ----- re-ranking tests @ backend/internal/rerank/rerank_test.go -----
package rerank

import (
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestEquityNeed(t *testing.T) {
	assert.InDelta(t, 1.0, EquityNeed(0), 0.001)
	assert.InDelta(t, 0.5, EquityNeed(1), 0.001)
	assert.InDelta(t, 1.0/3.0, EquityNeed(2), 0.001)
	assert.InDelta(t, 0.1, EquityNeed(9), 0.001)
	assert.InDelta(t, 1.0/101.0, EquityNeed(100), 0.001)
}

func TestFinalScore(t *testing.T) {
	score := FinalScore(0.9, 0, 0.7)
	assert.InDelta(t, 0.9*0.7+0.3*1.0, score, 0.001)

	score = FinalScore(0.9, 10, 0.7)
	assert.InDelta(t, 0.9*0.7+0.3*(1.0/11.0), score, 0.001)

	score = FinalScore(0.5, 0, 1.0)
	assert.InDelta(t, 0.5, score, 0.001)

	score = FinalScore(0.5, 0, 0.0)
	assert.InDelta(t, 1.0, score, 0.001)
}

func TestCollapseCandidatesByURL(t *testing.T) {
	candidates := []Candidate{
		{URL: "https://a.com", Score: 0.8, ChunkText: "lower"},
		{URL: "https://a.com", Score: 0.9, ChunkText: "higher"},
		{URL: "https://b.com", Score: 0.7, ChunkText: "only"},
	}

	result := CollapseCandidatesByURL(candidates)
	assert.Len(t, result, 2)

	urls := make(map[string]Candidate)
	for _, c := range result {
		urls[c.URL] = c
	}
	assert.Equal(t, "higher", urls["https://a.com"].ChunkText)
	assert.Equal(t, "only", urls["https://b.com"].ChunkText)
}

func TestCollapseCandidatesEmptyURL(t *testing.T) {
	candidates := []Candidate{
		{URL: "", Score: 0.8},
		{URL: "https://a.com", Score: 0.7},
	}
	result := CollapseCandidatesByURL(candidates)
	assert.Len(t, result, 1)
}

func TestRerankCandidates(t *testing.T) {
	InitLinkGraph(map[string]int{
		"https://a.com": 0,
		"https://b.com": 10,
		"https://c.com": 100,
	})

	candidates := []Candidate{
		{URL: "https://a.com", Score: 0.7},
		{URL: "https://b.com", Score: 0.8},
		{URL: "https://c.com", Score: 0.9},
	}

	result := RerankCandidates(candidates, 0.5, nil)
	assert.Len(t, result, 3)

	// With alpha=0.5, equity-heavy: orphans score higher
	assert.Equal(t, "https://a.com", result[0].URL)
}

func TestRerankCandidatesExcluded(t *testing.T) {
	InitLinkGraph(map[string]int{
		"https://a.com": 0,
		"https://b.com": 0,
	})

	candidates := []Candidate{
		{URL: "https://a.com", Score: 0.9},
		{URL: "https://b.com", Score: 0.8},
	}

	excluded := map[string]bool{"https://a.com": true}
	result := RerankCandidates(candidates, 0.7, excluded)
	assert.Len(t, result, 1)
	assert.Equal(t, "https://b.com", result[0].URL)
}

func TestRerankCandidatesEmpty(t *testing.T) {
	result := RerankCandidates([]Candidate{}, 0.7, nil)
	assert.Empty(t, result)
}

func TestGetLinkGraph(t *testing.T) {
	graph := map[string]int{"https://a.com": 5, "https://b.com": 3}
	InitLinkGraph(graph)

	result := GetLinkGraph()
	assert.Equal(t, 5, result["https://a.com"])
	assert.Equal(t, 3, result["https://b.com"])
}

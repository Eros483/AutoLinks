// ----- entity extraction tests @ backend/internal/extract/entities_test.go -----
package extract

import (
	"os"
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestNormalizeEntityText(t *testing.T) {
	tests := []struct {
		input    string
		expected string
	}{
		{"Hello World", "helloworld"},
		{"CUDA optimization", "cudaoptimization"},
		{"Machine Learning", "machinelearning"},
		{"  Spaces  ", "spaces"},
		{"hello-world!", "helloworld"},
		{"a@b#c$d", "abcd"},
	}
	for _, tt := range tests {
		result := normalizeEntityText(tt.input)
		assert.Equal(t, tt.expected, result)
	}
}

func TestToInitialism(t *testing.T) {
	tests := []struct {
		input    string
		expected string
	}{
		{"Artificial General Intelligence", "agi"},
		{"Machine Learning", "ml"},
		{"Hello", ""},
		{"A B C", "abc"},
		{"single", ""},
	}
	for _, tt := range tests {
		result := toInitialism(tt.input)
		assert.Equal(t, tt.expected, result)
	}
}

func TestPostProcessEntitiesDeduplication(t *testing.T) {
	entities := []Entity{
		{Text: "Machine Learning", Start: 0, End: 16, Label: "technology"},
		{Text: "Machine Learning", Start: 50, End: 66, Label: "technology"},
		{Text: "AI", Start: 0, End: 2, Label: "topic"},
		{Text: "Deep Learning", Start: 100, End: 113, Label: "technology"},
	}

	result := PostProcessEntities(entities, 5)
	assert.Equal(t, 2, len(result))
	texts := make(map[string]bool)
	for _, e := range result {
		texts[e.Text] = true
	}
	assert.True(t, texts["Machine Learning"])
	assert.True(t, texts["Deep Learning"])
}

func TestPostProcessEntitiesMinCharLength(t *testing.T) {
	entities := []Entity{
		{Text: "ab", Start: 0, End: 2, Label: "topic"},
		{Text: "abcde", Start: 10, End: 15, Label: "technology"},
	}
	result := PostProcessEntities(entities, 5)
	assert.Equal(t, 1, len(result))
	assert.Equal(t, "abcde", result[0].Text)
}

func TestPostProcessEntitiesEmpty(t *testing.T) {
	result := PostProcessEntities([]Entity{}, 5)
	assert.Empty(t, result)
}

func TestParseSSEDataSuccess(t *testing.T) {
	sseText := "event: complete\ndata: [\"hello world\"]\n"
	result, err := parseSSEData(sseText)
	assert.NoError(t, err)
	assert.Equal(t, "\"hello world\"", result)
}

func TestParseSSEDataError(t *testing.T) {
	sseText := "event: error\ndata: {\"error\":\"something went wrong\"}\n"
	_, err := parseSSEData(sseText)
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "space error")
}

func TestParseSSEDataUnexpected(t *testing.T) {
	_, err := parseSSEData("garbage data")
	assert.Error(t, err)
}

func TestGetFixtureEntities(t *testing.T) {
	result := getFixtureEntities("CUDA optimization is key for GPU computing")
	assert.Len(t, result, 1)
	assert.Equal(t, "CUDA optimization", result[0].Text)
}

func TestGetFixtureEntitiesNoMatch(t *testing.T) {
	result := getFixtureEntities("nothing matches here")
	assert.Empty(t, result)
}

func TestExtractEntitiesDryRun(t *testing.T) {
	original := os.Getenv("DRY_RUN")
	os.Setenv("DRY_RUN", "true")
	defer func() { os.Setenv("DRY_RUN", original) }()

	result, err := ExtractEntities("CUDA optimization in gradient descent")
	assert.NoError(t, err)
	assert.NotEmpty(t, result)
}

func TestExtractEntitiesNoModelsURL(t *testing.T) {
	original := os.Getenv("MODELS_SPACE_URL")
	os.Setenv("MODELS_SPACE_URL", "")
	os.Setenv("DRY_RUN", "false")
	defer func() {
		os.Setenv("MODELS_SPACE_URL", original)
		os.Setenv("DRY_RUN", "false")
	}()

	_, err := ExtractEntities("test")
	assert.ErrorIs(t, err, ErrNoEntities)
}

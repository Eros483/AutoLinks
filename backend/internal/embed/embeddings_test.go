// ----- embedding tests @ backend/internal/embed/embeddings_test.go -----
package embed

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestEmbedBatchNoModelSpaceURL(t *testing.T) {
	original := os.Getenv("MODELS_SPACE_URL")
	os.Setenv("MODELS_SPACE_URL", "")
	defer os.Setenv("MODELS_SPACE_URL", original)

	_, err := EmbedBatch([]string{"test"})
	assert.Error(t, err)
}

func TestEmbedBatchViaMockSpace(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method == "POST" {
			w.Header().Set("Content-Type", "application/json")
			json.NewEncoder(w).Encode(map[string]string{"event_id": "abc123"})
		} else {
			body := "event: complete\ndata: [\"[[0.1,0.2,0.3]]\"]\n"
			w.Write([]byte(body))
		}
	}))
	defer server.Close()

	original := os.Getenv("MODELS_SPACE_URL")
	os.Setenv("MODELS_SPACE_URL", server.URL)
	defer os.Setenv("MODELS_SPACE_URL", original)

	results, err := EmbedBatch([]string{"hello world"})
	assert.NoError(t, err)
	assert.Len(t, results, 1)
	assert.Len(t, results[0], 3)
	assert.InDelta(t, 0.1, results[0][0], 0.001)
	assert.InDelta(t, 0.2, results[0][1], 0.001)
	assert.InDelta(t, 0.3, results[0][2], 0.001)
}

func TestEmbedTextViaMockSpace(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method == "POST" {
			w.Header().Set("Content-Type", "application/json")
			json.NewEncoder(w).Encode(map[string]string{"event_id": "abc"})
		} else {
			body := "event: complete\ndata: [\"[[0.5,0.6]]\"]\n"
			w.Write([]byte(body))
		}
	}))
	defer server.Close()

	original := os.Getenv("MODELS_SPACE_URL")
	os.Setenv("MODELS_SPACE_URL", server.URL)
	defer os.Setenv("MODELS_SPACE_URL", original)

	result, err := EmbedText("hello")
	assert.NoError(t, err)
	assert.Len(t, result, 2)
}

func TestEmbedTextEmptyBatch(t *testing.T) {
	original := os.Getenv("MODELS_SPACE_URL")
	os.Setenv("MODELS_SPACE_URL", "")
	defer os.Setenv("MODELS_SPACE_URL", original)

	_, err := EmbedText("test")
	assert.Error(t, err)
}

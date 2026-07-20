// ----- latency evaluation: 50 sequential POSTs, P50/P95/P99 @ backend/eval/latency/main.go -----
package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"math"
	"net/http"
	"os"
	"sort"
	"time"
)

var testDrafts = []string{
	"The fundamental theorem of calculus connects differentiation and integration.",
	"Machine learning models require careful hyperparameter tuning.",
	"Quantum computing leverages superposition and entanglement.",
	"The mitochondria are the powerhouse of the cell.",
	"Climate change poses significant challenges to global food security.",
	"Natural language processing has advanced dramatically with transformer models.",
	"The human brain contains approximately 86 billion neurons.",
	"Blockchain technology provides decentralized consensus mechanisms.",
	"Photosynthesis converts light energy into chemical energy.",
	"Deep learning architectures like CNNs excel at image recognition.",
}

func main() {
	apiBase := os.Getenv("EVAL_API_URL")
	if apiBase == "" {
		apiBase = "http://localhost:8000/api/v1"
	}

	numRequests := 50
	fmt.Printf("Starting latency evaluation with %d requests\n", numRequests)
	fmt.Printf("API Base URL: %s\n", apiBase)

	var allLatencies []float64

	client := &http.Client{Timeout: 30 * time.Second}

	for i := 0; i < numRequests; i++ {
		draft := testDrafts[i%len(testDrafts)]

		reqBody, _ := json.Marshal(map[string]string{"text": draft})
		reqStart := time.Now()

		resp, err := client.Post(apiBase+"/recommend", "application/json", bytes.NewReader(reqBody))
		if err != nil {
			fmt.Printf("Request %d exception: %v\n", i+1, err)
			continue
		}
		reqEnd := time.Now()

		if resp.StatusCode != http.StatusOK {
			fmt.Printf("Request %d failed with status %d\n", i+1, resp.StatusCode)
			resp.Body.Close()
			continue
		}

		var data struct {
			LatencyMs int64 `json:"latency_ms"`
		}
		json.NewDecoder(resp.Body).Decode(&data)
		resp.Body.Close()

		latencyMs := float64(data.LatencyMs)
		if latencyMs == 0 {
			latencyMs = float64(reqEnd.Sub(reqStart).Milliseconds())
		}
		allLatencies = append(allLatencies, latencyMs)

		fmt.Printf("Request %d/%d: %.0fms\n", i+1, numRequests, latencyMs)
	}

	if len(allLatencies) == 0 {
		fmt.Println("No successful requests - cannot compute statistics")
		return
	}

	sort.Float64s(allLatencies)

	mean := mean(allLatencies)
	median := percentile(allLatencies, 0.5)
	minLat := allLatencies[0]
	maxLat := allLatencies[len(allLatencies)-1]
	stdev := stdDev(allLatencies, mean)
	p95 := percentile(allLatencies, 0.95)
	p99 := percentile(allLatencies, 0.99)

	targetMs := 3000.0
	passed := maxLat < targetMs

	fmt.Println()
	fmt.Println("============================================================")
	fmt.Println("LATENCY EVALUATION RESULTS (Eval 1)")
	fmt.Println("============================================================")
	fmt.Printf("Total Requests:       %d\n", numRequests)
	fmt.Printf("Successful:           %d\n", len(allLatencies))
	fmt.Printf("Failed:               %d\n", numRequests-len(allLatencies))
	fmt.Println("------------------------------------------------------------")
	fmt.Printf("Mean Latency:         %.2f ms\n", mean)
	fmt.Printf("Median Latency:       %.2f ms\n", median)
	fmt.Printf("Min Latency:          %.0f ms\n", minLat)
	fmt.Printf("Max Latency:          %.0f ms\n", maxLat)
	fmt.Printf("Std Dev:              %.2f ms\n", stdev)
	fmt.Printf("P95 Latency:          %.0f ms\n", p95)
	fmt.Printf("P99 Latency:          %.0f ms\n", p99)
	fmt.Println("------------------------------------------------------------")
	fmt.Printf("Target:               %.0f ms\n", targetMs)
	status := "PASS"
	if !passed {
		status = "FAIL"
	}
	fmt.Printf("Status:               %s\n", status)
	fmt.Println("============================================================")
}

func mean(values []float64) float64 {
	sum := 0.0
	for _, v := range values {
		sum += v
	}
	return sum / float64(len(values))
}

func stdDev(values []float64, mean float64) float64 {
	if len(values) <= 1 {
		return 0
	}
	sum := 0.0
	for _, v := range values {
		sum += (v - mean) * (v - mean)
	}
	return math.Sqrt(sum / float64(len(values)-1))
}

func percentile(sorted []float64, p float64) float64 {
	idx := int(math.Round(p * float64(len(sorted)-1)))
	if idx < 0 {
		idx = 0
	}
	if idx >= len(sorted) {
		idx = len(sorted) - 1
	}
	return sorted[idx]
}

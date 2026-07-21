// ----- batch throughput evaluation @ backend/eval/throughput/main.go -----
package main

import (
	"bytes"
	"encoding/json"
	"flag"
	"fmt"
	"net/http"
	"os"
	"time"
)

var apiBase string

func init() {
	apiBase = os.Getenv("EVAL_API_URL")
	if apiBase == "" {
		apiBase = "http://localhost:8000/api/v1"
	}
}

func main() {
	sitemapURL := flag.String("sitemap", "", "Sitemap URL to crawl for throughput measurement")
	flag.Parse()

	if *sitemapURL == "" {
		fmt.Println("Usage: go run ./eval/throughput --sitemap https://example.com/post-sitemap.xml")
		os.Exit(1)
	}

	resp, err := http.Get(apiBase + "/health")
	if err != nil || resp.StatusCode != http.StatusOK {
		fmt.Println("API not available. Start the server first.")
		if resp != nil {
			resp.Body.Close()
		}
		os.Exit(1)
	}
	resp.Body.Close()

	reqBody, err := json.Marshal(map[string]interface{}{
		"sitemap_url":    *sitemapURL,
		"max_concurrent": 5,
	})
	if err != nil {
		fmt.Printf("Failed to marshal request: %v\n", err)
		os.Exit(1)
	}

	fmt.Printf("Submitting sitemap ingest: %s\n", *sitemapURL)
	postResp, err := http.Post(apiBase+"/ingest/sitemap", "application/json", bytes.NewReader(reqBody))
	if err != nil {
		fmt.Printf("Failed to submit ingest: %v\n", err)
		os.Exit(1)
	}
	defer postResp.Body.Close()

	var submitResult struct {
		JobID             string `json:"job_id"`
		Status            string `json:"status"`
		EstimatedArticles int    `json:"estimated_articles"`
	}
	if err := json.NewDecoder(postResp.Body).Decode(&submitResult); err != nil {
		fmt.Printf("Failed to decode response: %v\n", err)
		os.Exit(1)
	}

	fmt.Printf("Job ID: %s, Estimated articles: %d\n", submitResult.JobID, submitResult.EstimatedArticles)
	fmt.Println()

	type snapshot struct {
		elapsed      float64
		articlesDone int
		total        int
		status       string
	}

	var history []snapshot
	start := time.Now()

	client := &http.Client{Timeout: 10 * time.Second}
	pollInterval := 1 * time.Second

	var prevDone int
	for {
		time.Sleep(pollInterval)

		resp, err := client.Get(apiBase + "/ingest/status/" + submitResult.JobID)
		if err != nil {
			fmt.Printf("Poll error: %v\n", err)
			continue
		}

		var status struct {
			Status       string  `json:"status"`
			ProgressPct  float64 `json:"progress_pct"`
			ArticlesDone int     `json:"articles_done"`
			Total        int     `json:"total"`
		}
		json.NewDecoder(resp.Body).Decode(&status)
		resp.Body.Close()

		elapsed := time.Since(start).Seconds()

		articlesDone := status.ArticlesDone
		total := status.Total

		history = append(history, snapshot{
			elapsed:      elapsed,
			articlesDone: articlesDone,
			total:        total,
			status:       status.Status,
		})

		instantRate := 0.0
		if len(history) > 1 {
			delta := float64(articlesDone - prevDone)
			instantRate = delta / pollInterval.Seconds()
		}

		fmt.Printf("  [%6.1fs] %s | done=%d/%d (%5.1f%%) | rate: %.1f art/s\n",
			elapsed, status.Status, articlesDone, total, status.ProgressPct, instantRate)

		prevDone = articlesDone

		if status.Status == "done" || status.Status == "failed" {
			if status.Status == "done" {
				duration := elapsed
				throughput := float64(articlesDone) / duration
				peakRate := 0.0
				for i, s := range history {
					if i == 0 {
						continue
					}
					delta := float64(s.articlesDone - history[i-1].articlesDone)
					iv := s.elapsed - history[i-1].elapsed
					if iv > 0 {
						r := delta / iv
						if r > peakRate {
							peakRate = r
						}
					}
				}

				fmt.Println()
				fmt.Println("============================================================")
				fmt.Println("BATCH THROUGHPUT EVALUATION RESULTS")
				fmt.Println("============================================================")
				fmt.Printf("  Sitemap:              %s\n", *sitemapURL)
				fmt.Printf("  Articles:             %d\n", articlesDone)
				fmt.Printf("  Duration:             %.1fs\n", duration)
				fmt.Printf("  Throughput:           %.2f articles/sec\n", throughput)
				fmt.Printf("  Peak throughut:       %.2f articles/sec\n", peakRate)
				fmt.Printf("  Concurrent fetches:   5\n")
				fmt.Println("============================================================")

				if throughput > 2.5 {
					fmt.Println("RESULT: Throughput GOOD (>2.5 articles/sec)")
				} else {
					fmt.Println("RESULT: Throughput LOW (<2.5 articles/sec)")
				}
			}
			break
		}
	}
}

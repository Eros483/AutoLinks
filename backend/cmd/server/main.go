// ----- HTTP server entry point with goroutine worker pool @ backend/cmd/server/main.go -----
package main

import (
	"fmt"
	"net/http"

	"github.com/anomalyco/autolinks/internal/config"
	"github.com/anomalyco/autolinks/internal/handlers"
	"github.com/anomalyco/autolinks/internal/jobs"
	"github.com/anomalyco/autolinks/internal/logger"
	"github.com/anomalyco/autolinks/internal/qdrant"
	"github.com/anomalyco/autolinks/internal/rerank"
)

func main() {
	logger.Info("Starting %s", config.AppName())

	if err := qdrant.EnsureCollection(384); err != nil {
		logger.Error("Failed to ensure Qdrant collection: %s", err)
	}

	rerank.RestoreLinkGraph()

	handlers.WorkerPool = jobs.NewWorkerPool()

	if config.Debug() {
		logger.Info("Debug mode enabled")
	}
	if config.DryRun() {
		logger.Warning("DRY_RUN enabled - using fixture data")
	}

	router := handlers.NewRouter()

	port := config.Port()
	addr := fmt.Sprintf(":%s", port)
	logger.Info("Server listening on %s", addr)

	if err := http.ListenAndServe(addr, router); err != nil {
		logger.Error("Server failed: %s", err)
	}
}

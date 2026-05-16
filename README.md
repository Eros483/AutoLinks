<div align="center">

# AutoLinks

</center>

<center>
<p>
  <img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.109+-blue.svg" alt="FastAPI">
  <img src="https://img.shields.io/badge/Qdrant-2.8+-blue.svg" alt="Qdrant">
  <img src="https://img.shields.io/badge/GLiNER-via%20pioneer.ai-blue.svg" alt="GLiNER">
  <img src="https://img.shields.io/badge/React-18.2-blue.svg" alt="React">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
<!-- Code Quality -->
  <a href="https://github.com/psf/black">
    <img src="https://img.shields.io/badge/code%20style-black-000000.svg" alt="Code Style: Black">
  </a>

  <!-- Deployments -->
  <a href="https://autolinks-api.onrender.com">
    <img src="https://img.shields.io/badge/Render-Deployed-success?logo=render" alt="Render Deployment">
  </a>
  <a href="https://autolinks.vercel.app">
    <img src="https://img.shields.io/badge/Vercel-Deployed-black?logo=vercel" alt="Vercel Deployment">
  </a>

  <!-- Project Activity & License -->
  <a href="https://github.com/yourusername/AutoLinks/commits/main">
    <img src="https://img.shields.io/github/last-commit/Eros483/AutoLinks?logo=github" alt="Last Commit">
  </a>
  <a href="https://opensource.org/licenses/MIT">
    <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License: MIT">
  </a>
</p>
</center>

<p>A semantic internal link generation API that analyzes draft text, extracts named entities using GLiNER, finds semantically similar articles via Qdrant vector search, and returns high-confidence internal linking recommendations with equity-aware re-ranking.</p>

---
<div align="left">

## Features

- **Named Entity Extraction** - Uses GLiNER XL 1B to identify entities from draft text
- **Semantic Search** - Vector similarity search using all-MiniLM-L6-v2 embeddings
- **Equity-Aware Ranking** - Re-ranks recommendations to prioritize orphan pages
- **Sitemap Ingestion** - Crawl and index articles from any sitemap URL
- **Graph Diagnostics** - Logs orphan counts, top inbound URLs, and skipped sitemap targets for debugging link-graph quality
- **Synthetic Equity Eval** - Deterministic benchmark mode for testing equity improvements without relying on a real sitemap
- **REST API** - FastAPI-based API with automatic OpenAPI documentation
- **React Frontend** - Modern UI for testing link recommendations

---

## Quick Start

### 1. Clone & Setup

```bash
git clone https://github.com/yourusername/AutoLinks.git
cd AutoLinks
```

### 2. Backend Setup

```bash
cd backend

# Using Conda as package manager, so move to your preferred environment/package manager.
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your credentials:
# - PIONEER_API_KEY: Get from https://pioneer.ai
# - QDRANT_URL: Local Qdrant URL (default: http://localhost:6333)
# - QDRANT_API_KEY: Leave empty for local Qdrant
```

### 4. Run the Server Locally

```bash
# Spinning up qdrant docker container
docker run -p 6333:6333 -p 6334:6334 -v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant

# Development (with auto-reload)
uvicorn backend.main:app --reload
```

The API will be available at `http://localhost:8000`. Visit `http://localhost:8000/docs` for the interactive Swagger UI.

### 5. Frontend Setup

The frontend is a React 18 + Vite application using Zustand for state management and vanilla CSS (no Tailwind).

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

The frontend runs on `http://localhost:3000` and reads the backend API base URL from the repo-root `.env` file using `VITE_API_BASE_URL`.

**Environment Requirements:**
- Backend must be running at the URL configured in `VITE_API_BASE_URL`
- Qdrant must be running for the backend to return recommendations

Example local setting:

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

### 6. Run Tests

```bash
cd backend

# All tests
pytest

# Specific test directories
pytest tests/test_api/
pytest tests/test_core/

# With coverage
pytest --cov=. --cov-report=html
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/recommend` | POST | Analyze text and get link recommendations |
| `/api/v1/ingest` | POST | Ingest a single article |
| `/api/v1/ingest/sitemap` | POST | Crawl and ingest from sitemap |
| `/api/v1/health` | GET | Health check |

Full API usage, request examples, and response shapes: [docs/api.md](docs/api.md)

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PIONEER_API_KEY` | GLiNER API key from pioneer.ai | - |
| `QDRANT_API_KEY` | Optional Qdrant API key for hosted deployments | empty |
| `QDRANT_URL` | Qdrant URL | `http://localhost:6333` |
| `DRY_RUN` | Skip GLiNER API, use fixtures | `false` |
| `DEBUG` | Enable debug mode | `false` |
| `RERANK_ALPHA` | Similarity weight for re-ranking | `0.7` |

---

## Development

### Code Formatting

```bash
cd backend
black .
```

### Testing with DRY_RUN

To test without spending GLiNER credits:

```bash
DRY_RUN=true uvicorn backend.main:app --reload
```

This returns fixture entity data while still running the full embedding, search, and re-ranking pipeline.

---

## Architecture

- **Frontend**: React + Vite + Zustand (deployed on Vercel)
- **Backend**: FastAPI (deployed on Render)
- **NER**: GLiNER XL 1B via pioneer.ai API
- **Vector DB**: Qdrant Cloud Serverless (local for development)
- **Embeddings**: all-MiniLM-L6-v2 (local, ~200MB RAM)

Full design and architecture thought for the project: [docs/design.md](docs/design.md)

---

## Evaluation

The project includes evaluation scripts to measure performance and equity distribution:

### Eval 1 - Latency Evaluation

```bash
cd backend
python -m eval.eval_latency
```

Measures total round-trip time across 50 sequential requests. Target: under 3 seconds. Reports mean, median, P95, P99 latencies.

**Latest latency benchmark result**  
Run date: `2026-05-15`
- Requests: `50/50` successful
- Mean latency: `1529.32 ms`
- Max latency: `4103 ms`
- Target: `< 3000 ms`
- Outcome: average performance is comfortably within target, but the worst-case request still exceeded the 3-second ceiling

### Eval 2 - AI Precision (LLM-as-a-Judge)

```bash
cd backend
DEBUG=false PYTHONPATH=. python -m eval.eval_precision
```

Measures semantic accuracy of generated internal-link recommendations using Groq as the judge model. The evaluator sends the recommendation output through a Groq-hosted LLM with richer source and target context, then records `YES` or `NO` verdicts on whether each recommendation is semantically accurate and genuinely helpful.

The current Eval 2 implementation uses the official Groq Python SDK with `llama-3.3-70b-versatile` as the judge model.

**Latest precision benchmark result**
- Judge provider: `Groq`
- Judge model: `llama-3.3-70b-versatile`
- YES verdict rate: `83%`

### Eval 4 - Link Equity Distribution

```bash
cd backend
python -m eval.eval_equity
```

Compares α=1.0 (baseline, pure similarity) vs α=0.7 (equity-aware) across 50 drafts. Computes Gini coefficient and orphan reduction rate to verify equity-aware re-ranking distributes links intelligently.

For unreliable real-world sitemaps, there is also a synthetic benchmark mode:

```bash
cd backend
DEBUG=false PYTHONPATH=. python -m eval.eval_equity --mode synthetic
```

The synthetic mode builds a deterministic constrained link graph with orphan, low-link, mid-link, and highly linked pages, then evaluates the same reranking logic against controlled candidate pools. This makes it possible to measure equity behavior even when a sitemap produces a noisy or unrealistic internal-link graph.

**Latest synthetic benchmark result**
- Baseline Gini: `0.6734`
- Equity-aware Gini: `0.5382`
- Absolute Gini reduction: `0.1352`
- Relative Gini reduction: `20.08%`
- Orphan reduction: `0.00%` -> `100.00%`

The live sitemap-backed eval now also logs graph diagnostics, including orphan counts, top inbound URLs, unmatched internal-link targets, and rescued orphan samples, so it is easier to tell whether poor results come from the reranker or from the source link graph itself.

**Environment Variable:** Set `EVAL_API_URL` to override default `http://localhost:8000/api/v1`

---

## License

MIT

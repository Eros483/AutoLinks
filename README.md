<div align="center">

# AutoLinks
## 

</center>

<center>
<p>
  <img src="https://img.shields.io/badge/Go-1.25+-00ADD8.svg?logo=go&logoColor=white" alt="Go">
  <img src="https://img.shields.io/badge/chi-v5-00ADD8.svg?logo=go&logoColor=white" alt="chi">
  <img src="https://img.shields.io/badge/Qdrant-1.18+-blue.svg" alt="Qdrant">
  <img src="https://img.shields.io/badge/GLiNER2-HF%20Space-blue.svg" alt="GLiNER2">
  <img src="https://img.shields.io/badge/React-18.2-blue.svg" alt="React">
<!-- Code Quality -->
  <a href="https://go.dev/blog/gofmt">
    <img src="https://img.shields.io/badge/code%20style-gofmt-00ADD8.svg?logo=go&logoColor=white" alt="Code Style: go fmt">
  </a>

  <!-- Deployments -->
  <a href="https://autolinks-api.onrender.com">
    <img src="https://img.shields.io/badge/Render-Deployed-success?logo=render" alt="Render Deployment">
  </a>
  <a href="https://autolinks.vercel.app">
    <img src="https://img.shields.io/badge/Vercel-Deployed-black?logo=vercel" alt="Vercel Deployment">
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

---

##  Local Usage

### 1. Clone & Setup

```bash
git clone https://github.com/yourusername/AutoLinks.git
cd AutoLinks
```

### 2. Backend Setup

```bash
cd backend

# Download Go dependencies
go mod download
```

### 3. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your credentials:
# - MODELS_SPACE_URL: HF Space for GLiNER + embeddings
# - HF_TOKEN: Hugging Face access token
# - QDRANT_URL: Qdrant endpoint (http://localhost:6334 or cloud)
# - QDRANT_API_KEY: Qdrant API key (optional for local)
# - REDIS_URL: Redis for job queue and link graph
# - GROQ_API_KEY: To run the precision eval (LLM-as-a-judge)
```

### 4. Run the Server Locally

```bash
# Spinning up qdrant docker container
docker run -p 6333:6333 -p 6334:6334 -v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant

# Development (with DRY_RUN for fixture data)
go run ./cmd/server
```

The API will be available at `http://localhost:8000`.

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
go test ./...

# With race detector (recommended for goroutine-heavy code)
go test -race ./...

# With coverage
go test -coverprofile=coverage.out ./...
```

---

## Further Documentation

- Architecture Decisions: [docs/design.md](docs/design.md)
- Deployment strategies: [docs/deployment.md](docs/deployment.md)
- Full API usage, request examples, and response shapes: [docs/api.md](docs/api.md)
- AI Evals: [docs/design.md](docs/design.md)

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MODELS_SPACE_URL` | HF Space for GLiNER + MiniLM inference | - |
| `HF_TOKEN` | Hugging Face access token | - |
| `QDRANT_API_KEY` | Optional Qdrant API key for hosted deployments | empty |
| `QDRANT_URL` | Qdrant endpoint (HTTP for local, HTTPS for cloud) | `http://localhost:6334` |
| `REDIS_URL` | Redis for job queue and link graph | - |
| `GROQ_API_KEY` | Groq LLM for precision eval | - |
| `DRY_RUN` | Skip HF Space calls, use fixtures | `false` |
| `DEBUG` | Enable debug mode | `false` |
| `RERANK_ALPHA` | Similarity weight for re-ranking | `0.7` |

---

## License

MIT

---

## License

MIT
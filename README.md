<div align="center">

# AutoLinks
## 

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

# Using uv as the project manager.
uv init
uv add -r requirements.txt
```

### 3. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your credentials:
# - PIONEER_API_KEY: Get from https://pioneer.ai
# - QDRANT_URL: Local Qdrant URL (default: http://localhost:6333)
# - QDRANT_API_KEY: Leave empty for local Qdrant
# - GROQ_API_KEY: To run tests for LLM as a judge
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

## Further Documentation

- Architecture Decisions: [docs/design.md](docs/design.md)
- Deployment strategies: [docs/deployment.md](docs/deployment.md)
- Full API usage, request examples, and response shapes: [docs/api.md](docs/api.md)
- AI Evals: [docs/evals.md](docs/evals.md)

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PIONEER_API_KEY` | GLiNER API key from pioneer.ai | - |
| `QDRANT_API_KEY` | Optional Qdrant API key for hosted deployments | empty |
| `QDRANT_URL` | Qdrant URL | `http://localhost:6333` |
| `GROQ_API_KEY` | LLM served via Groq for LLM as a judge | - |
| `DRY_RUN` | Skip GLiNER API, use fixtures | `false` |
| `DEBUG` | Enable debug mode | `false` |
| `RERANK_ALPHA` | Similarity weight for re-ranking | `0.7` |

---

## License

MIT

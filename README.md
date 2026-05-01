<h1>AutoLinks</h1>

<p>
  <img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.109+-blue.svg" alt="FastAPI">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
</p>

<p>A semantic internal link generation API that analyzes draft text, extracts named entities using GLiNER, finds semantically similar articles via Qdrant vector search, and returns high-confidence internal linking recommendations with equity-aware re-ranking.</p>

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

# Install dependencies with uv
uv sync
```

### 4. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your credentials:
# - PIONEER_API_KEY: Get from https://pioneer.ai
# - QDRANT_URL: Local Qdrant URL (default: http://localhost:6333)
# - QDRANT_API_KEY: Leave empty for local Qdrant
```

### 5. Run the Server

```bash
# Development (with auto-reload)
uvicorn main:app --reload

# Or run directly
python -m uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`. Visit `http://localhost:8000/docs` for the interactive Swagger UI.

### 6. Run Tests

```bash
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
black .
```

### Testing with DRY_RUN

To test without spending GLiNER credits:

```bash
DRY_RUN=true uvicorn main:app --reload
```

This returns fixture entity data while still running the full embedding, search, and re-ranking pipeline.

---

## Architecture

- **Frontend**: React + Vercel (planned)
- **Backend**: FastAPI on Render
- **NER**: GLiNER XL 1B via pioneer.ai
- **Vector DB**: Qdrant (local for development)
- **Embeddings**: all-MiniLM-L6-v2 (local)

See `docs/design.MD` for full architecture details.

---

## TODO

- [ ] Fix Qdrant issues, linked below.
```
500 Internal Server Error
/home/arnab/miniconda3/envs/autolinks/lib/python3.11/site-packages/qdrant_client/qdrant_remote.py:288: UserWarning: Failed to obtain server version. Unable to check client-server compatibility. Set check_compatibility=False to skip version check.
  show_warning(
^CINFO:     Shutting down
INFO:     Waiting for application shutdown.
INFO:     Application shutdown complete.
INFO:     Finished server process [55764]
INFO:     Stopping reloader process [55757]
```

- [ ] Consider swapping to `Moss` for vector DB, might fit on render and docs say its faster than qdrant and similiar

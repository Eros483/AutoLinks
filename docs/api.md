# AutoLinks API Guide

This guide explains how to run the API locally, what each endpoint expects, and what shape to expect back.

## Base URL

Local development:

```text
http://127.0.0.1:8000
```

Versioned API prefix:

```text
/api/v1
```

Swagger UI is available at:

```text
http://127.0.0.1:8000/docs
```

---

## Start The API

From the backend directory:

```bash
go run ./cmd/server
```

Environment variables are loaded from the project root `.env` file.

If you want to avoid external API calls during development:

```bash
DRY_RUN=true go run ./cmd/server
```

The server starts an HTTP server on port 8000 and an in-process goroutine worker pool for background sitemap ingestion jobs.

---

## Response Conventions

Successful recommendation responses return:

- `status`
- `latency_ms`
- `recommendations`

Validation errors usually return HTTP `422`.

Application errors usually return HTTP `500` with a `detail` field.

---

## `POST /api/v1/recommend`

Analyze draft text and return internal link recommendations.

### Request Body

```json
{
  "text": "CUDA optimization can dramatically speed up model training.",
  "alpha": 0.7,
  "min_similarity": 0.65
}
```

### Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `text` | string | yes | Draft text to analyze |
| `alpha` | float | no | Similarity weight in the equity-aware rerank formula |
| `min_similarity` | float | no | Minimum vector similarity score required before a candidate is surfaced |

### Example cURL

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/recommend" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Wait But Why is organizing a global meetup this weekend.",
    "alpha": 0.7,
    "min_similarity": 0.65
  }'
```

### Example Response

```json
{
  "status": "success",
  "latency_ms": 720,
  "recommendations": [
    {
      "exact_phrase": "Wait But Why",
      "context_snippet": "A post about the Wait But Why community and meetup planning.",
      "suggested_url": "https://example.com/wait-but-why-meetup",
      "similarity_score": 0.82,
      "equity_need_score": 0.5,
      "final_score": 0.724,
      "inbound_link_count": 1
    }
  ]
}
```

### Notes

- Short noisy entities are filtered before search.
- Abbreviation duplicates such as `WBW` and `Wait But Why` are deduplicated before query generation.
- Low-similarity candidates below `min_similarity` are not returned.

---

## `POST /api/v1/ingest`

Ingest a single article into Qdrant.

### Request Body

```json
{
  "url": "https://example.com/blog/cuda-optimization",
  "content": "CUDA optimization improves GPU throughput by reducing memory bottlenecks..."
}
```

### Example cURL

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/blog/cuda-optimization",
    "content": "CUDA optimization improves GPU throughput by reducing memory bottlenecks..."
  }'
```

### Example Response

```json
{
  "status": "success",
  "chunks_ingested": 1
}
```

### Notes

- The API chunks article text before embedding and upserting to Qdrant.
- Stored payload includes the source URL and chunk text.

---

## `POST /api/v1/ingest/sitemap`

Crawl a sitemap, extract article content, build the internal link graph, and ingest the articles.

### Request Body

```json
{
  "sitemap_url": "https://example.com/post-sitemap.xml",
  "max_concurrent": 5
}
```

### Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `sitemap_url` | string | yes | Sitemap to crawl |
| `max_concurrent` | integer | no | Max concurrent fetches during crawl |

### Example cURL

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/ingest/sitemap" \
  -H "Content-Type: application/json" \
  -d '{
    "sitemap_url": "https://example.com/post-sitemap.xml",
    "max_concurrent": 5
  }'
```

### Example Response

```json
{
  "status": "success",
  "chunks_ingested": 150
}
```

### Notes

- The crawler extracts clean text with `trafilatura`.
- The same crawl also extracts internal `<a href>` links from page HTML.
- Those links are inverted into inbound link counts and used by the equity-aware reranker.

---

## `GET /api/v1/health`

Simple health check endpoint.

### Example cURL

```bash
curl "http://127.0.0.1:8000/api/v1/health"
```

### Example Response

```json
{
  "status": "ok",
  "model_loaded": true
}
```

---

## Common Workflow

1. Start Qdrant.
2. Start the Go server.
3. Ingest existing content with `/api/v1/ingest` or `/api/v1/ingest/sitemap`.
4. Send draft text to `/api/v1/recommend`.
5. Render the returned recommendations in your frontend or CMS integration.

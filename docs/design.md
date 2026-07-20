# AutoLinks — Semantic Internal Link Generation API

> A feature addition to [inlinks.com/internal-linking-tool](https://inlinks.com/internal-linking-tool/)

---

## 1. The Problem Statement

Managing internal link equity is a massive, expensive bottleneck for digital publishers and SEO teams.

**The Manual Bottleneck.** Content teams waste hours manually searching through site archives to find relevant past articles to link to. Pages that get missed become orphan pages, bleeding link equity and failing to rank on Google.

**The Context Problem.** Existing automated tools rely on primitive keyword matching (regex). This produces irrelevant, spammy links because the tools lack semantic understanding — they cannot differentiate "Apple" the tech giant from "Apple" the fruit.

**The Integration Nightmare.** Tools that attempt to inject links directly into the DOM often break page formatting, slow down page load times, and require complex, error-prone HTML parsing.

---

## 2. The Solution

A decoupled API that semantically analyzes draft text and returns high-confidence internal linking recommendations.

Instead of an automated bot that forcibly changes a database or scrapes the web, AutoLinks is an intelligent backend service. It receives a raw text payload and returns a clean JSON map of specific entities, target internal URLs, and confidence scores. It is designed to be mathematically precise and easily integrable into any modern CMS or standalone frontend.

**What separates AutoLinks from existing tools** is that it treats internal link equity as a finite resource being allocated across a network — not just a relevance score on a single query. Every link recommendation is made with awareness of the site's full link graph, so equity is distributed intelligently rather than reflexively concentrated on already well-linked pages.

---

## 3. Architecture

```
Vercel (Frontend)
      ↓
Go/chi on Render (Orchestrator)
      ↓                  ↓                  ↓
HF Space             Qdrant Cloud      Link Graph Store
(GLiNER2 + MiniLM)   (Vector DB)       (inbound link counts
(eros483/autolinks)   gRPC port 6334    per URL in Redis,
                                        built from sitemap
                                        at ingestion)
```

Three services. No GPU infrastructure. No model downloads. Total ongoing infrastructure cost: $0.

---

## 4. Tech Stack & Service Breakdown

### A. Frontend (Vercel)

**Stack:** React or Next.js

**Role:** A lightweight, globally distributed static site. Provides a clean text editor for the user to paste their draft and renders the API's JSON response as interactive, clickable link-suggestion cards.

---

### B. Orchestrator (Go/chi on Render)

**Stack:** Go, chi router

**Role:** The central traffic cop. Receives incoming requests from the frontend, handles authentication and rate limiting, and orchestrates the two downstream API calls.

**Why this works on Render's free tier:** With all model inference offloaded to HuggingFace Space (`eros483/autolinks-models`), the service is genuinely lightweight. No local models are loaded in-process. The Go binary uses ~25MB RAM at runtime, well within Render's 512MB limit.

**Async job processing:** Sitemap ingestion runs on an in-process goroutine worker pool (4 workers). No separate Celery/Render Background Worker service is needed — the goroutine pool starts with the HTTP server. Jobs are tracked in Redis, with retry (3 attempts, exponential backoff 30s→60s→120s) and a dead letter queue for permanently failed jobs. A scheduled ping from cron-job.org hits a `/health` endpoint every 10 minutes to prevent the instance from spinning down.

---

### C. NER Engine + Embeddings (HF Space — eros483/autolinks-models)

**Stack:** HuggingFace Space, no local infrastructure

**Role:** A combined Space hosting both GLiNER2 (entity extraction) and all-MiniLM-L6-v2 (sentence embeddings). Receives raw draft text via `POST /extract` and returns named entities with position offsets. Receives text batches via `POST /embed` and returns 384-dimensional embedding vectors.

To preserve credits during development, a `DRY_RUN=true` environment flag skips the HF Space calls and returns hardcoded fixture data for both entity extraction and embeddings. All downstream Qdrant and re-ranking logic runs normally.

---

### D. Vector Database (Qdrant Cloud Serverless)

**Stack:** Qdrant (free serverless tier), accessed via gRPC (port 6334)

**Role:** Stores the vector embeddings of all existing published articles alongside their URL metadata. When the orchestrator receives entities from the HF Space, it generates a sentence-level context embedding for each entity, then queries Qdrant via cosine similarity search to find the most semantically relevant existing article.

**Chunking strategy:** Articles are embedded at the paragraph or 3–5 sentence sliding window level, not sentence-by-sentence. This preserves enough surrounding context that short or ambiguous sentences ("Apple reported earnings") are disambiguated by their neighbors. The parent article URL is stored as metadata on each chunk.

**Ingestion:** A lightweight `POST /ingest` endpoint on the FastAPI service accepts a URL and content payload, generates the chunk embeddings, and upserts them into Qdrant. This is run once per article, either manually or triggered via a CMS webhook.

---

### E. Link Graph Store (Equity-Aware Ranking Layer)

**Stack:** Redis (Upstash free tier), built at ingestion time

**Role:** Maintains a count of inbound internal links per URL across the site. This data is built once from the site's `sitemap.xml` at ingestion and updated incrementally as new articles are ingested. Stored under Redis key `autolinks:link_graph` and restored into memory on server startup. It powers the equity-aware re-ranking step that runs after Qdrant returns candidate URLs.

**How it's built:** On ingestion, the orchestrator parses the sitemap to inventory all URLs, then crawls each page's outbound internal links to construct the graph. Each URL is stored with its current inbound link count:

```python
link_graph = {
    "https://site.com/blog/gradient-descent": 34,
    "https://site.com/blog/backpropagation": 12,
    "https://site.com/blog/cuda-optimization": 1,
    "https://site.com/blog/spatial-computing": 0,  # orphan
}
```

**The re-ranking formula:** After Qdrant returns the top-k candidate URLs with their cosine similarity scores, the orchestrator computes a combined final score:

```
equity_need = 1 / (1 + inbound_link_count)
final_score = α × similarity_score + (1 - α) × equity_need
```

Where `α` is a tunable weight (default: 0.7). A page with 0 inbound links scores an equity_need of 1.0. A page with 50 inbound links scores ~0.02. This means a highly relevant orphan page can outrank a slightly more similar but already well-linked page — which is precisely the intended behavior.

`α` is exposed as a user-configurable parameter. SEO teams in a "rescue orphans" phase dial it toward 0.5. Teams in a "consolidate authority" phase dial it toward 0.9. The tunability is itself a product feature.

---

## 5. The Deliverable (Clean JSON)

The API returns actionable, renderable data. The frontend maps each recommendation to an interactive suggestion card. The `equity_need_score` is surfaced explicitly so users understand why a recommendation was made.

```json
{
  "status": "success",
  "latency_ms": 720,
  "recommendations": [
    {
      "exact_phrase": "CUDA optimization",
      "context_snippet": "...resulting in massive gains through CUDA optimization.",
      "suggested_url": "https://company.com/blog/gpu-memory-profiling",
      "similarity_score": 0.91,
      "equity_need_score": 0.83,
      "final_score": 0.94,
      "inbound_link_count": 1
    },
    {
      "exact_phrase": "spatial computing",
      "context_snippet": "...pushing the boundaries of spatial computing.",
      "suggested_url": "https://company.com/blog/spatial-computing-guide",
      "similarity_score": 0.89,
      "equity_need_score": 0.12,
      "final_score": 0.71,
      "inbound_link_count": 34
    }
  ]
}
```

---

## 6. Latency Model

Entity extraction and embedding generation are both handled by the same HF Space. Qdrant queries are structurally sequential (embeddings are generated after entities are returned), but all calls are fast enough that the total round trip is well under the 3-second target on warm instances. The equity re-ranking step is an in-memory lookup and adds negligible latency.

| Step | Estimated Duration |
|---|---|
| HF Space: entity extraction (GLiNER2) | 300–600ms |
| HF Space: embedding generation (MiniLM) | ~100ms |
| Qdrant cosine similarity query (gRPC) | 50–100ms |
| Equity re-ranking (in-memory) | <5ms |
| JSON serialization (compiled Go) | ~1–2ms |
| **Total (warm)** | **~470–820ms** |

Cold starts on Render are mitigated by the cron ping. The HF Space is a managed service with no cold start exposure.

---

## 7. Evaluation Metrics

### Eval 1 — Distributed Systems Performance (Latency)

**Metric:** Total round-trip time from Vercel request to JSON response, measured across 50 sequential calls.

**Target:** Under 3 seconds. Expected actual: under 1 second on warm instances.

**Instrumentation:** Each segment of the pipeline (GLiNER call, embedding, Qdrant query, equity re-ranking) is logged independently so bottlenecks are identifiable, not just the aggregate.

---

### Eval 2 — AI Precision (LLM-as-a-Judge)

**Metric:** Semantic accuracy of the suggested links.

**Pipeline:** A test suite of 50 drafts is passed through the API. Each recommendation is fed to a frontier model with the prompt: *"Given this sentence context and the suggested link, is this a semantically accurate and highly helpful resource? Reply YES or NO."*

**Target:** >90% YES rate, proving that vector similarity successfully handles context and defeats keyword-matching ambiguity.

**Judge model:** Cheap model from Groq, leveraging free tier.

**Mandatory tripwire cases:** The eval suite explicitly includes 5–10 ambiguity test cases (e.g., "Apple" in food context vs. tech context, "Python" as language vs. snake). A >90% overall pass rate without correctly handling these specific cases is not considered a pass.

---

### Eval 3 — Credit Burn Rate

**Metric:** GLiNER API cost per request, logged during the eval run.

**Target:** Establish a per-recommendation cost baseline before any external demo. Ensures the $75 credit pool is not silently exhausted.

---

### Eval 4 — Link Equity Distribution (Graph Health)

**Metric:** How intelligently the system distributes link equity across the site, compared to a pure similarity baseline.

**Why this matters:** A system that always links to the most similar article will reflexively concentrate links on already well-linked pages, leaving orphan pages dark and unrankable. This eval proves that equity-aware re-ranking fixes that without degrading semantic quality.

**Pipeline:** Take a real site's sitemap. Run the same 50 drafts through two configurations:
- **Baseline:** Pure similarity (`α = 1.0`)
- **Equity-aware:** Combined scoring (`α = 0.7`)

For each configuration, record which URLs were recommended and compute two metrics on the resulting simulated link graph:

**Orphan reduction rate** — percentage of currently zero-inbound-link pages that received at least one recommendation. Higher is better.

**Gini coefficient of link distribution** — a value between 0 and 1 measuring inequality of link concentration. 0 means every page receives equal links. 1 means one page absorbs all links. Equity-aware should produce a meaningfully lower Gini than the baseline.

**Target:** Equity-aware system achieves a lower Gini coefficient and higher orphan reduction rate than the pure similarity baseline, while maintaining >90% semantic accuracy on Eval 2.

**The key result** is a two-axis plot: X axis is semantic accuracy (Eval 2 score), Y axis is link equity distribution health (Gini coefficient). Pure similarity occupies one corner. The equity-aware system occupies a better corner — proving the system redistributes equity without sacrificing relevance. That is the central claim of the product, quantified.

---

## 8. Corpus Ingestion

### The Cold Start Problem

The recommendation engine has nothing to recommend until articles are indexed in Qdrant and the link graph is populated. Ingestion is therefore the prerequisite to everything — both for real user onboarding and for internal testing.

---

### Ingestion Pipeline (Sitemap Crawler + Trafilatura)

When a site owner onboards, or when we ingest a corpus for testing, the flow is:

1. **Parse the sitemap index** — hit `sitemap.xml` to find sub-sitemaps. For a WordPress site this is typically a Yoast-generated index pointing to `post-sitemap.xml`, `page-sitemap.xml`, etc. Only the post sitemap is relevant.
2. **Extract all article URLs** — parse `post-sitemap.xml` to get every published URL with its last-modified date.
3. **Crawl and extract clean text** — for each URL, fetch the raw HTML and extract clean article body text using `go-trafilatura`. This handles nav stripping, ads, footers, and comment sections automatically — no custom HTML parsing required.
4. **Chunk, embed, and upsert** — pipe the clean text through the existing `/ingest` endpoint: chunk into 3–5 sentence windows, generate embeddings with `all-MiniLM-L6-v2`, upsert into Qdrant with the source URL as metadata.
5. **Build the link graph** — during the same crawl, extract all internal `<a href>` links from each page to populate the inbound link count map.

```python
import trafilatura
import requests
import time
from xml.etree import ElementTree

# 1. Parse the post sitemap
response = requests.get("https://waitbutwhy.com/post-sitemap.xml")
tree = ElementTree.fromstring(response.content)
urls = [elem.text for elem in tree.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]

# 2. Crawl and extract
for url in urls:
    html = trafilatura.fetch_url(url)
    text = trafilatura.extract(html)
    if text:
        # send to /ingest endpoint
        pass
    time.sleep(1)  # polite crawl delay
```

> Note: The above snippet is conceptual — the actual implementation uses `go-trafilatura` in Go with a goroutine worker pool for parallel crawling, retry with exponential backoff, and Redis-backed job tracking. See the migration plan (`docs/migrate-to-go.md`) for details.

**Concurrent crawling:** The naive sequential crawl (one URL, 1s sleep, repeat) takes 2–3 minutes for 150 articles. The ingestion pipeline instead uses a goroutine-based worker pool with a bounded semaphore to parallelize fetches, reducing ingestion time to under 30 seconds and making the approach viable for any corpus over a few hundred articles.

The semaphore bounds concurrency to 5 simultaneous requests — enough to get meaningful parallelism without triggering rate limiting or overwhelming a shared host. Failures are caught per-URL and logged without crashing the entire run. Workers retry failed URLs up to 3 times with exponential backoff (30s → 60s → 120s) before sending them to a dead letter queue in Redis for manual inspection.

**For ongoing ingestion:** The RSS feed (`/feed`) acts as a webhook equivalent — polling it periodically surfaces new articles as they are published, so only new content needs to be ingested rather than re-crawling the full sitemap.

| Trigger | Use Case |
|---|---|
| `post-sitemap.xml` crawl | One-time bulk ingestion (onboarding or testing setup) |
| RSS feed poll | Incremental ingestion of new articles |

---

### Test Corpus: Wait But Why

For development and evaluation, the corpus is sourced from **Wait But Why** (`waitbutwhy.com`). It was selected because it has a coherent topic cluster (long-form essays on science, technology, and human behavior), a realistic volume of articles (~150 posts), a public sitemap, and enough cross-referential content to produce meaningful linking recommendations.

**Sitemap entry point:** `https://waitbutwhy.com/sitemap_index.xml`

This index contains three sub-sitemaps:

| Sitemap | Contents | Used |
|---|---|---|
| `https://waitbutwhy.com/post-sitemap.xml` | All published posts | ✅ Yes — primary corpus |
| `https://waitbutwhy.com/table-sitemap.xml` | Data tables | ❌ No |
| `https://waitbutwhy.com/post_tag-sitemap.xml` | Tag pages | ❌ No |

Only `post-sitemap.xml` is ingested. The other two contain no article content relevant to link recommendations.

The full ingestion of ~150 articles at 1 second per request takes approximately 2–3 minutes. This is run once during setup and produces the Qdrant index and link graph that all subsequent evals and demos run against.

---

## 9. Testing

The test suite is written in Go using the standard `testing` package with `testify/assert` for assertions and `miniredis` for Redis mocking. Tests are co-located with their target package as `*_test.go` files and cover three layers: unit tests for core logic, integration tests for the API endpoints, and mocked tests for external service calls. The full suite can be run with `go test ./...` from the `backend/` directory.

---

### Unit Tests

**Re-ranking formula** — the equity-aware scoring function is pure logic with no external dependencies. Tests verify correctness across edge cases:

```go
func TestRerankingPrefersOrphanOverPopular(t *testing.T) {
    orphanScore := finalScore(similarity: 0.85, inboundLinks: 0, alpha: 0.7)
    popularScore := finalScore(similarity: 0.91, inboundLinks: 48, alpha: 0.7)
    assert.Greater(t, orphanScore, popularScore)
}

func TestAlpha1IsPureSimilarity(t *testing.T) {
    score := finalScore(similarity: 0.88, inboundLinks: 0, alpha: 1.0)
    assert.InDelta(t, 0.88, score, 0.001)
}

func TestZeroInboundLinksMaxEquityNeed(t *testing.T) {
    assert.Equal(t, 1.0, equityNeed(0))
}

func TestHighInboundLinksLowEquityNeed(t *testing.T) {
    assert.Less(t, equityNeed(100), 0.02)
}
```

**Chunking logic** — verifies that the sliding window chunker produces correctly sized chunks and doesn't drop content at article boundaries.

**Sitemap parser** — verifies URL extraction from both sitemap index format and flat sitemap format.

---

### Integration Tests (httptest)

Go's `httptest` package lets the full API be exercised in-process with no running server required. External calls (HF Space, Qdrant) are mocked so tests are fast, free, and deterministic.

```go
func TestRecommendReturnsCorrectShape(t *testing.T) {
    // Mock entity extraction and Qdrant search
    router := chi.NewRouter()
    router.Post("/api/v1/recommend", makeRecommendHandler(mockExtract, mockSearch))

    body := `{"text": "We saw gains through CUDA optimization.", "alpha": 0.7, "min_similarity": 0.65}`
    req := httptest.NewRequest("POST", "/api/v1/recommend", strings.NewReader(body))
    req.Header.Set("Content-Type", "application/json")
    w := httptest.NewRecorder()
    router.ServeHTTP(w, req)

    assert.Equal(t, 200, w.Code)
    var resp RecommendResponse
    json.Unmarshal(w.Body.Bytes(), &resp)
    assert.Equal(t, "success", resp.Status)
    assert.NotEmpty(t, resp.Recommendations)
    assert.Equal(t, "CUDA optimization", resp.Recommendations[0].ExactPhrase)
}

func TestRecommendEmptyTextReturns400(t *testing.T) { ... }
func TestHealthEndpoint(t *testing.T) { ... }
```

---

## 10. Infrastructure Summary

| Component | Service | Cost |
|---|---|---|
| Frontend | Vercel | Free |
| Orchestrator + Background Jobs | Go/chi on Render (single web service, goroutine worker pool in-process) | Free |
| Named Entity Recognition + Embeddings | HF Space (eros483/autolinks-models) | Free (zero-gpu CPU basic) |
| Vector Database | Qdrant Cloud Serverless (gRPC, port 6334) | Free |
| Link Graph Store + Job State + DLQ | Upstash Redis (free tier) | Free |
| Cron keepalive | cron-job.org or GitHub Actions | Free |
| **Total ongoing infrastructure** | | **$0** |


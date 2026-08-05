# AutoLinks — Full Project Walkthrough

> A semantic internal-link recommendation engine for SEO teams and content publishers.

---

## Table of Contents

1. [What This Project Is](#1-what-this-project-is)
2. [Why It Exists — The Problem and the Insight](#2-why-it-exists--the-problem-and-the-insight)
3. [Architecture Overview](#3-architecture-overview)
4. [The Request Lifecycle — Step by Step](#4-the-request-lifecycle--step-by-step)
5. [Frontend — React + Zustand on Vercel](#5-frontend--react--zustand-on-vercel)
6. [Backend — Go / chi on Render](#6-backend--go--chi-on-render)
   - 6.1 [Entry Point and Lifecycle](#61-entry-point-and-lifecycle)
   - 6.2 [Configuration](#62-configuration)
   - 6.3 [Logging](#63-logging)
   - 6.4 [Qdrant Client](#64-qdrant-client)
   - 6.5 [Entity Extraction](#65-entity-extraction)
   - 6.6 [Embedding Generation](#66-embedding-generation)
   - 6.7 [Vector Search](#67-vector-search)
   - 6.8 [Equity-Aware Re-Ranking](#68-equity-aware-re-ranking)
   - 6.9 [HTTP Handlers and CORS](#69-http-handlers-and-cors)
   - 6.10 [Authentication](#610-authentication)
   - 6.11 [Data Models](#611-data-models)
7. [Ingestion Pipeline](#7-ingestion-pipeline)
   - 7.1 [Text Chunking](#71-text-chunking)
   - 7.2 [Sitemap Crawl and Content Extraction](#72-sitemap-crawl-and-content-extraction)
   - 7.3 [Link Graph Construction](#73-link-graph-construction)
   - 7.4 [Async Job Queue](#74-async-job-queue)
   - 7.5 [Dead Letter Queue](#75-dead-letter-queue)
8. [Evaluation Suite](#8-evaluation-suite)
   - 8.1 [Eval 1 — Latency](#81-eval-1--latency)
   - 8.2 [Eval 2 — AI Precision (LLM-as-a-Judge)](#82-eval-2--ai-precision-llm-as-a-judge)
   - 8.3 [Eval 4 — Link Equity Distribution](#83-eval-4--link-equity-distribution)
9. [Infrastructure and Deployment](#9-infrastructure-and-deployment)
10. [Testing Strategy](#10-testing-strategy)
11. [Configuration Reference](#11-configuration-reference)

---

## 1. What This Project Is

AutoLinks takes a piece of draft text (a blog post, article, or page copy), analyzes it to find phrases that should link to other pages on the same website, and returns a ranked list of internal linking suggestions. Each suggestion tells you:

- **Which phrase** in your draft should become a link (e.g. "gradient descent")
- **Which URL** on your site it should point to (e.g. `https://example.com/blog/backprop-explained`)
- **Why** — through transparent scoring that separates semantic similarity from link equity need

It is not a CMS plugin. It does not modify your database or DOM. It is a stateless HTTP API that receives text and returns JSON. The frontend you see at `autolinks-seo.vercel.app` renders those JSON responses as interactive, highlight-linked recommendation cards, but the API can be called from anywhere — a headless CMS, a CLI script, a browser extension, or a CI pipeline.

---

## 2. Why It Exists — The Problem and the Insight

### The Manual Bottleneck

SEO teams and content publishers spend hours manually searching through their site archives to find relevant past articles to link to. Every new article needs 3–10 internal links to distribute authority through the site, and finding the right destination pages means: remembering what exists in the archive, searching the CMS by keyword, skimming each candidate page to verify the topic match, and repeating until enough good links are found. This is slow, error-prone, and rarely systematic — it depends entirely on the author's memory of what's in the archive.

### The Keyword-Matching Failure

Existing automated tools work through primitive keyword matching or regex. They look for exact string matches of key phrases, which produces two predictable failures:

1. **Irrelevant links.** "Apple" the tech company and "Apple" the fruit are the same string. "Python" the programming language and "Python" the snake match identically. Tools without semantic understanding cannot disambiguate.
2. **Missed opportunities.** A draft about "gradient descent" should link to an article about "backpropagation," but no exact keyword overlap means the tool finds nothing.

### The Equity Blindness

Even when tools _do_ find relevant articles, they operate purely on relevance ranking — most similar first. This has a structural side effect: the system reflexively concentrates links on the site's most prominent, already well-linked pages while leaving orphan (zero-inbound-link) pages permanently invisible to search crawlers. Over time, this creates an inequitable link distribution where 20% of pages hoard 80% of internal links, and the rest never get discovered.

### The Insight

AutoLinks treats internal link equity as a finite resource being allocated across a network. It is aware of the site's _entire_ link graph — which pages are popular, which are orphaned — and uses that awareness at recommendation time. A highly relevant orphan page can outrank a slightly more similar but already well-linked page. This is not a relevance problem solved with better embedding models. It's a resource allocation problem solved with a tunable mathematical model: **α × similarity + (1 - α) × equity_need**.

The tunability of α is itself a feature. SEO teams in a "rescue orphans" phase dial α toward 0.5. Teams in a "consolidate authority" phase dial it toward 0.9. The model is transparent enough that the operator understands _why_ a recommendation was made because both scores are surfaced explicitly in the API response.

---

## 3. Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                     Vercel (Frontend)                             │
│  React 18 + Vite 5 + Zustand + Clerk Auth                        │
│  autolinks-seo.vercel.app                                        │
└────────────────────────────┬─────────────────────────────────────┘
                             │ HTTPS
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│               Go / chi on Render (Orchestrator)                    │
│  Single binary, goroutine worker pool, Clerk JWT auth             │
│  autolinks-api.onrender.com                                      │
└──────┬──────────────────┬───────────────────┬───────────────────┘
       │ HTTPS (Gradio)   │ gRPC (port 6334)  │ TLS (Upstash)
       ▼                  ▼                   ▼
┌──────────────┐  ┌───────────────┐  ┌──────────────────┐
│  HF Space    │  │  Qdrant Cloud │  │  Upstash Redis   │
│  GLiNER2 +   │  │  Vector DB    │  │  Link Graph      │
│  MiniLM      │  │  (cosine)     │  │  Job State       │
│  eros483/    │  │  free tier    │  │  Dead Letter Q   │
│  autolinks-  │  │               │  │                  │
│  models      │  │               │  │                  │
└──────────────┘  └───────────────┘  └──────────────────┘
```

**Three external services. Zero GPU infrastructure. Zero local model loading in the Go process. Total ongoing cost: $0.**

The Go orchestrator binary uses ~25MB RAM at idle and starts in under one second. Both model inference tasks (entity extraction with GLiNER2 and sentence embedding with MiniLM) are offloaded to a shared HuggingFace Space running on HF's free CPU tier. Qdrant Cloud provides the vector database on its free serverless tier. Upstash Redis provides persistent storage for the link graph, async job tracking, and the dead letter queue — also free tier.

A scheduled GitHub Actions workflow pings all four services every 10 minutes to prevent free-tier sleep on Render, HF, and Qdrant.

---

## 4. The Request Lifecycle — Step by Step

Here is exactly what happens when a user pastes text and clicks "Analyze."

### Step 1: Frontend Collects Input

The user types or pastes text into the `Editor` component's `<textarea>`. The text is stored in a Zustand store (`draftText`) via `setDraftText()`. The user clicks the "Analyze" button, which triggers `handleAnalyze()` in `Editor.jsx`.

The Editor calls `fetchRecommendations(draftText, 0.7, 0.65, getToken)` from `services/api.js`. The `getToken` function comes from Clerk's `useAuth()` hook and retrieves a short-lived JWT that authenticates the user with the backend. The `api.js` layer constructs a POST to `<api-base>/recommend` with this body:

```json
{
  "text": "The draft content...",
  "alpha": 0.7,
  "min_similarity": 0.65
}
```

### Step 2: Handler Receives the Request

The Go server receives the POST at `/api/v1/recommend`. If `CLERK_SECRET_KEY` is configured in the environment, the `RequireAuth` middleware runs first: it extracts the `Bearer` token from the `Authorization` header, calls `clerk.Client.VerifyToken()` to validate the JWT, and injects the Clerk user ID into the request context. If the token is invalid or missing, the middleware returns `401 Unauthorized` before the handler ever runs.

The `handleRecommend` function in `handlers/routes.go` then:

1. Decodes the JSON body into a `RecommendRequest` struct
2. Validates that `text` is non-empty (returns `400` if not)
3. Applies defaults: `alpha = 0.7` if unset, `min_similarity = 0.65` if unset
4. Records the start time for latency measurement

### Step 3: Entity Extraction (GLiNER2 via HF Space)

The handler calls `extract.ExtractEntities(req.Text)`. This function runs the entire GLiNER2 pipeline:

1. If `DRY_RUN=true`, it returns three hardcoded fixture entities that are matched against the text
2. Otherwise, it calls `extract.CallSpace("extract_entities", text, labelsJSON)` which:
   - POSTs a Gradio API request to `{MODELS_SPACE_URL}/gradio_api/call/extract_entities`
   - Receives an `event_id` from the Gradio response
   - Polls the event endpoint (`GET {url}/{event_id}`) with exponential backoff starting at 500ms, up to 30 attempts
   - Parses the SSE text stream looking for `event: complete` or `event: error`
   - Extracts the JSON data from the `data:` SSE line
   - Unmarshals the returned JSON array into `[]Entity` structs

The returned entities have four fields:
- `Text`: the entity string (e.g. "gradient descent")
- `Start` / `End`: character offsets in the original text
- `Label`: the GLiNER label (e.g. "concept", "technology", "person")

GLiNER is called with five label types: `person`, `organization`, `topic`, `technology`, and `concept`. This creates broad coverage — the model is instructed to find entities matching any of these categories rather than being given a fixed list of entity types to detect.

If `ExtractEntities` returns an `ErrNoEntities` sentinel error, the handler returns `400 - No high-quality entities found in text`. If it returns any other error (HF Space down, network failure, timeout), the handler returns `500 - Entity extraction failed`.

### Step 4: Entity Post-Processing

The raw GLiNER output is noisy. The handler passes entities through `extract.PostProcessEntities(entities, minCharLength=5)`:

- **Trim whitespace** and normalize to lowercase alphanumeric for comparison
- **Filter by minimum length** — entities shorter than 5 normalized characters are discarded (catches noise like "AI", "ML", "API" which are too short to be meaningful linking anchors)
- **Deduplicate** — entities that normalize to the same string are collapsed to the first occurrence
- **Initialism deduplication** — if an entity like "Natural Language Processing" exists, its initialism "nlp" is computed, and any short alpha-only entity matching that initialism is discarded to avoid both "Natural Language Processing" and "NLP" generating separate recommendations for the same concept

The handler then trims to the top 10 entities (by GLiNER's original ordering, which roughly corresponds to confidence).

### Step 5: Query Construction

For each entity, the handler constructs a query string by concatenating the entity text with the first 200 characters of the draft:

```
"gradient descent - The draft content about optimizing neural networks through careful learning rate scheduling and gradient descent..."
```

This enriches the embedding query with context from the surrounding text. A bare entity like "gradient descent" embedded alone would match any article about gradient descent. With the draft context prepended, the query embedding is pulled toward articles that discuss gradient descent _in a similar context_ to the draft.

### Step 6: Batch Embedding

All queries (up to 10) are sent in a single call to `embed.EmbedBatch(queries)`. This is a critical optimization — instead of 10 separate HTTP round trips to HF Space, all queries travel in one request and return in one response.

`EmbedBatch` calls `extract.CallSpace("embed_text", textsJSON)` which follows the exact same Gradio API call/poll pattern as entity extraction. The `embed_text` endpoint on the HF Space runs `all-MiniLM-L6-v2` and returns 384-dimensional float64 vectors.

**Error in this step is now fatal.** If the embedding service is unavailable, the handler returns `500 - Embedding service unavailable` rather than silently returning an empty recommendation list (which was the earlier behavior — a bug since fixed).

### Step 7: Parallel Qdrant Search

With one embedding vector per entity, the handler launches a goroutine for each entity. The goroutine pool pattern uses a channel + WaitGroup:

```go
resultCh := make(chan entityResult, len(validEntities))
var wg sync.WaitGroup

for i, e := range validEntities {
    wg.Add(1)
    go func(entity extract.Entity, embedding []float64) {
        defer wg.Done()
        candidates, err := search.SearchSimilar(embedding, 100, minSimilarity)
        resultCh <- entityResult{entity: entity, candidates: convertToRerankCandidates(candidates)}
    }(e, allEmbeddings[i])
}

go func() { wg.Wait(); close(resultCh) }()
```

Each goroutine calls `search.SearchSimilar(embedding, limit=100, minScore=0.65)`, which:

1. Converts the float64 embedding to float32 (Qdrant's native format)
2. Creates a `QueryPoints` request with the collection name, query vector, limit, score threshold, and a flag to include payloads
3. Executes the gRPC query against Qdrant Cloud with a 30-second timeout
4. Converts the Qdrant protobuf response into `SearchResult` structs, checking for nil payload fields to prevent panics
5. Returns up to 100 candidates per entity

This parallel search is the primary latency optimization. For a typical request with 4–7 entities, all Qdrant queries run concurrently rather than sequentially.

### Step 8: Equity-Aware Re-Ranking

The handler collects all goroutine results and iterates through them. For each entity's candidate set, it calls `rerank.RerankCandidates(candidates, alpha, selectedURLs)`.

The re-ranker operates in three stages:

**Stage 1 — Collapse to one per URL.** A single article appears as multiple Qdrant points (one per chunk). Multiple chunks from the same article matching the same entity would crowd out other articles. The re-ranker collapses chunk-level hits to the best-scoring chunk per URL using `CollapseCandidatesByURL`.

**Stage 2 — Exclude already-selected URLs.** The `selectedURLs` map tracks which destination URLs have already been assigned to earlier entities in the recommendation set. This ensures the final recommendations list contains unique destination URLs — the same article won't be suggested for multiple entities in one batch.

**Stage 3 — Score computation.** For each remaining unique URL, the re-ranker computes:

```
equity_need(URL) = 1 / (1 + inbound_link_count(URL))
final_score       = α × similarity_score + (1 - α) × equity_need
```

The inbound link count comes from the in-memory link graph (`rerank.linkGraph`), a `map[string]int` protected by `sync.RWMutex`. This graph is built during sitemap ingestion (see Section 7.3) and persisted to Redis under key `autolinks:link_graph`. On server startup, it is restored from Redis by `RestoreLinkGraph()`.

The equity need formula creates a sharp curve:
- 0 inbound links → equity_need = **1.00** (maximum need)
- 1 inbound link → equity_need = **0.50**
- 10 inbound links → equity_need = **0.09**
- 50 inbound links → equity_need = **0.02**
- 100 inbound links → equity_need = **0.01** (effectively saturated)

With the default α = 0.7, the weighting is 70% similarity and 30% equity need. An orphan page with similarity 0.85 would score `0.7 × 0.85 + 0.3 × 1.0 = 0.895`, outranking a well-linked page with similarity 0.93 that scores `0.7 × 0.93 + 0.3 × 0.03 = 0.660`.

Candidates are sorted by descending `final_score` and the top results are selected.

### Step 9: Response Assembly

The handler builds `Recommendation` structs, each containing:

```json
{
  "exact_phrase": "gradient descent",
  "context_snippet": "The first 150 chars of the matched chunk...",
  "suggested_url": "https://example.com/blog/backprop-explained",
  "similarity_score": 0.91,
  "equity_need_score": 0.83,
  "final_score": 0.886,
  "inbound_link_count": 1
}
```

The final list is capped at 10 recommendations and sorted by descending `final_score`. The response includes total `latency_ms` measured from handler entry to JSON serialization start.

### Step 10: Frontend Rendering

The `Editor` component receives the response, calls `setRecommendations(result.recommendations, result.latency)` on the Zustand store, and switches the editor from textarea mode to highlight overlay mode.

The `buildHighlightedHtml()` function in `editor_highlight.js` takes the draft text and the recommendation list:

1. HTML-escapes the entire draft text to prevent XSS
2. Builds a set of unique entity phrases from the recommendations
3. For each phrase, wraps occurrences with `<mark class="hl" data-phrase-key="...">` tags
4. Returns the marked-up HTML string, which is rendered via `dangerouslySetInnerHTML`

The `Recommendations` component renders each recommendation as a `Card` component. Clicking a card sets `activeCardId` in the store, which triggers a `useEffect` in the Editor that:
- Finds all `<mark>` elements with the matching `data-phrase-key` attribute
- Scrolls the first matching mark into view
- Adds a `pulse` CSS class to all matching marks for 1400ms

Each card displays the exact phrase, a context snippet from the matched chunk, the destination URL as a clickable link, and two score badges: Match (similarity) and Equity (equity need).

---

## 5. Frontend — React + Zustand on Vercel

### File Structure

```
frontend/src/
├── components/
│   ├── App.jsx            # Root: view router (home/workspace/sitemap)
│   ├── Header.jsx         # Navigation bar with Clerk user button
│   ├── LandingPage.jsx    # Marketing/landing view
│   ├── Layout.jsx         # Composes Editor + Recommendations side by side
│   ├── Editor.jsx         # Text input, analyze trigger, highlight rendering
│   ├── Recommendations.jsx # Card list, loading/empty/error states
│   ├── Card.jsx           # Single recommendation card
│   └── SitemapPage.jsx    # Sitemap status check + crawl submission
├── services/
│   └── api.js             # All API calls, auth token injection, error handling
├── store/
│   └── store.js           # Zustand store: draft, recommendations, theme, errors
├── utils/
│   └── editor_highlight.js # HTML escape, phrase highlighting, phrase key encoding
└── index.css              # All styles (no framework)
```

### View Routing

The app uses component-state routing (no React Router). `App.jsx` maintains `currentView` state (`'home'`, `'workspace'`, `'sitemap'`). The `Header` component passes `onNavigate` which calls `setCurrentView`. The home page (`LandingPage`) renders without auth. The workspace and sitemap views are wrapped in `<SignedIn>` / `<SignedOut>` from Clerk.

### State Management (Zustand)

The Zustand store (`store.js`) is a single source of truth for:

| Field | Type | Purpose |
|-------|------|---------|
| `draftText` | string | Current editor content |
| `recommendations` | array | API response recommendations |
| `loading` | boolean | Whether analysis is in progress |
| `error` | string | Error message if analysis fails |
| `latency` | number | Last response latency in ms |
| `activeCardId` | number | Index of the highlighted recommendation card |
| `theme` | string | 'light', 'dark', or 'system' (persisted to localStorage) |

The `setRecommendations` action atomically sets recommendations, latency, clears loading, clears error, and resets `activeCardId`. This prevents stale state from leaking across requests.

Theme is applied by setting `data-theme` on `<html>`. In system mode, it listens to the `prefers-color-scheme` media query.

### Clerk Authentication

The frontend uses `@clerk/clerk-react` with `ClerkProvider` wrapping the app in `main.jsx`. The `Header` component renders `UserButton` from Clerk for sign-in/sign-out. The `Editor` and `SitemapPage` components use `useAuth().getToken` to retrieve a short-lived JWT that is passed through `api.js` as a `Bearer` token on every API request.

If the Clerk publishable key is not configured, auth is effectively no-op — the `SignedIn`/`SignedOut` wrappers in `App.jsx` render nothing.

### API Layer

`services/api.js` provides three exported functions and two helpers:

- `getApiBaseUrl(env)` — reads `VITE_API_BASE_URL` from env vars, falls back to `http://127.0.0.1:8000/api/v1`, strips trailing slash
- `buildApiUrl(path)` — constructs full URL from path
- `authHeaders(token)` — returns headers dict with optional Bearer token
- `resolveToken(getToken)` — shared async helper that calls `getToken()` if provided
- `handleApiError(response)` — shared error extraction that reads `detail` from JSON error bodies and throws
- `fetchRecommendations(text, alpha, minSimilarity, getToken)` — POST `/recommend`
- `fetchSitemapStatus(getToken)` — GET `/link-graph`
- `ingestSitemap(sitemapUrl, maxConcurrent, getToken)` — POST `/ingest/sitemap`

### Dev Server

Vite is configured to proxy `/api` requests to the backend in development. The proxy target is derived from `VITE_API_BASE_URL` at build time. The frontend dev server runs on port `3000`. The env file is read from the repo root (one level above `frontend/`) via `envDir: path.resolve(__dirname, '..')`.

---

## 6. Backend — Go / chi on Render

The backend is a single Go binary. There is no separate worker process, no Celery, no Redis-based task broker for the worker pool. The goroutine worker pool starts and stops with the HTTP server.

### 6.1 Entry Point and Lifecycle

`cmd/server/main.go` is the only public entry point. The `main()` function runs a linear startup sequence:

1. **Logger initialization** — the `logger` package's `init()` function creates the `logs/` directory and opens a date-stamped log file. Logs are written with timestamp, level (INFO/WARNING/ERROR/FATAL), and message. The file handle is protected by a mutex.

2. **Qdrant collection assurance** — `qdrant.EnsureCollection(384)` checks if the `articles` collection exists and creates it with cosine distance and 384-dimensional vectors if it doesn't. This is now **fatal** on failure — if Qdrant is unreachable at startup, the server exits rather than running in a degraded state.

3. **Link graph restoration** — `rerank.RestoreLinkGraph()` reads the serialized link graph from Redis key `autolinks:link_graph` and populates the in-memory `rerank.linkGraph` map. If Redis is unreachable or the key doesn't exist, the server starts with an empty graph.

4. **Worker pool creation** — `jobs.NewWorkerPool()` creates a buffered channel (capacity 100) and spawns 4 goroutines that block on the channel, waiting for jobs.

5. **Clerk client initialization** — if `CLERK_SECRET_KEY` is set, a `clerk.Client` is created. Failure here is **fatal**. If the key is not set, auth is disabled globally and a warning is logged.

6. **HTTP server startup** — a `http.Server` is configured with read/write/idle timeouts and the chi router as handler. The server runs in a goroutine. The main goroutine blocks on a signal channel listening for `SIGINT` and `SIGTERM`. On signal receipt, it calls `srv.Shutdown()` with a 30-second timeout to drain in-flight requests gracefully.

### 6.2 Configuration

`internal/config/config.go` provides typed access to all environment variables. On package init, `godotenv.Load()` is called to load a `.env` file from the working directory. All config values are exposed as anonymous functions (closures) that read from `os.Getenv` on each call. This pattern was chosen during migration from Python and serves the same purpose: deferred evaluation so config can change between calls (useful in tests).

The available config values:

| Function | Env Var | Default | Type |
|----------|---------|---------|------|
| `QdrantAPIKey()` | `QDRANT_API_KEY` | `""` | string |
| `HFToken()` | `HF_TOKEN` | `""` | string |
| `GroqAPIKey()` | `GROQ_API_KEY` | `""` | string |
| `QdrantURL()` | `QDRANT_URL` | `http://localhost:6334` | string |
| `ModelsSpaceURL()` | `MODELS_SPACE_URL` | `""` | string |
| `GroqURL()` | `GROQ_URL` | `https://api.groq.com/...` | string |
| `AppName()` | `APP_NAME` | `AutoLinks` | string |
| `Debug()` | `DEBUG` | `false` | bool |
| `DryRun()` | `DRY_RUN` | `false` | bool |
| `GroqModel()` | `GROQ_MODEL` | `llama-3.3-70b-versatile` | string |
| `QdrantCollection()` | `QDRANT_COLLECTION` | `articles` | string |
| `EmbeddingModel()` | `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | string |
| `RerankAlpha()` | `RERANK_ALPHA` | `0.7` | float64 |
| `RedisURL()` | `REDIS_URL` | `""` | string |
| `ClerkSecretKey()` | `CLERK_SECRET_KEY` | `""` | string |
| `FrontendURL()` | `FRONTEND_URL` | `localhost:3000,autolinks-seo.vercel.app` | string |
| `Port()` | `PORT` | `8000` | string |

Type coercion is handled by `GetBool` (uses `strconv.ParseBool`), `GetFloat` (`strconv.ParseFloat`), and `GetInt` (`strconv.Atoi`). Parse errors return the zero value silently.

### 6.3 Logging

The `logger` package provides four functions: `Info()`, `Warning()`, `Error()`, and `Fatal()`. Each formats with `fmt.Sprintf`, prepends a timestamp and level, and writes to the log file under a mutex. `Fatal` additionally calls `os.Exit(1)`.

Log files are named `log_YYYY-MM-DD.log` inside the `logs/` directory. There is no log rotation — the file name changes daily, but old files are never cleaned up. For production, log rotation should be handled externally.

### 6.4 Qdrant Client

The Qdrant client is initialized lazily and once using `sync.Once`. On first access, the `QDRANT_URL` is parsed to extract host, port, and TLS settings. If the host contains `cloud.qdrant.io` or the scheme is `https`, TLS is enabled. The API key is passed from config.

`EnsureCollection(vectorSize)` checks collection existence and creates it with cosine distance if needed. This runs at startup but could also be triggered explicitly.

The `SearchPerformer()` function is an alias for `GetClient()` — it exists to provide a named interface for search callers.

### 6.5 Entity Extraction

**Package:** `internal/extract`

**Key types:**
- `Entity` — `{Text, Start, End, Label}` with JSON tags
- `DefaultEntityLabels` — the five GLiNER label types

**Key functions:**

`ExtractEntities(text string) ([]Entity, error)` — the main entry point. Three paths:

1. **DRY_RUN mode:** Calls `getFixtureEntities()` which matches hardcoded fixtures (`"CUDA optimization"`, `"spatial computing"`, `"gradient descent"`) against the text via case-insensitive `strings.Contains`.
2. **No MODELS_SPACE_URL:** Returns `ErrNoEntities` sentinel error.
3. **Normal path:** Calls `CallSpace("extract_entities", text, labelsJSON)`, then double-unmarshals the result (Gradio wraps responses in an extra JSON string layer).

`CallSpace(endpoint string, args ...string) (string, error)` — the generic Gradio Space caller:

1. POSTs to `{MODELS_SPACE_URL}/gradio_api/call/{endpoint}` with `{"data": args}`
2. Reads the `event_id` from the response
3. Polls `GET {url}/{event_id}` with exponential backoff (500ms → 750ms → 1125ms → ... capped at 5s)
4. Returns the raw SSE body when `event: complete` or `event: error` is detected
5. Passes the SSE body to `parseSSEData` which extracts and unmarshals the JSON data

`PostProcessEntities(entities, minCharLength)` — filters, deduplicates, and removes initialism duplicates.

### 6.6 Embedding Generation

**Package:** `internal/embed`

`EmbedBatch(texts []string) ([][]float64, error)` calls `CallSpace("embed_text", textsJSON)` and double-unmarshals the result. Returns 384-dimensional vectors for each input text. If `MODELS_SPACE_URL` is empty, returns an error immediately.

`EmbedText(text string) ([]float64, error)` is a convenience wrapper around `EmbedBatch` for single-text embeddings.

### 6.7 Vector Search

**Package:** `internal/search`

`SearchSimilar(queryEmbedding []float64, limit int, minScore float64) ([]SearchResult, error)`:

1. Converts float64 embedding to float32
2. Creates a `QueryPoints` protobuf request with the collection name, query vector, limit, score threshold, and `WithPayload: true`
3. Executes against Qdrant gRPC with a 30-second timeout
4. Maps points to `SearchResult` structs, with nil checks on payload fields to prevent panics from malformed Qdrant responses

The search uses Qdrant's native cosine similarity — the `Distance_Cosine` was configured at collection creation time.

### 6.8 Equity-Aware Re-Ranking

**Package:** `internal/rerank`

**Key types:**
- `Candidate` — `{URL, ChunkText, Score, InboundLinkCount, EquityNeedScore, FinalScore}`

**Key functions:**

`InitLinkGraph(graph map[string]int)` — replaces the in-memory link graph and persists to Redis.

`RestoreLinkGraph() map[string]int` — restores the link graph from Redis key `autolinks:link_graph` into the package-level `linkGraph` variable.

`EquityNeed(inboundLinks int) float64` — computes `1 / (1 + inbound_links)`.

`FinalScore(similarity float64, inboundLinks int, alpha float64) float64` — computes `α × similarity + (1 - α) × equity_need`.

`CollapseCandidatesByURL(candidates []Candidate) []Candidate` — deduplicates by URL, keeping the highest-scoring chunk per URL.

`RerankCandidates(candidates []Candidate, alpha float64, excludedURLs map[string]bool) []Candidate` — the full re-ranking pipeline:
1. Collapses to one per URL
2. Excludes already-selected URLs
3. Reads inbound link counts from the thread-safe `linkGraph` map (using `RLock`)
4. Computes equity need and final scores
5. Sorts by descending final score

`GetLinkGraph() map[string]int` — returns a copy of the current link graph.

**Redis client:** The rerank package maintains its own Redis connection via `getRedisClient()`, initialized once with `sync.Once`. It connects using `REDIS_URL` from config.

### 6.9 HTTP Handlers and CORS

**Package:** `internal/handlers`

The `NewRouter(tokenVerifier)` function builds a chi router with:

| Middleware | Purpose |
|-----------|---------|
| `middleware.Logger` | Logs every HTTP request (chi built-in) |
| `middleware.Recoverer` | Recovers from panics, returns 500 |
| `middleware.RequestID` | Injects request IDs |
| `cors.Handler(...)` | CORS with allowed origins from `FRONTEND_URL` |
| `requestBodyLimiter(1MB)` | Rejects POST bodies >1MB |
| `auth.RequireAuth(...)` | Clerk JWT verification (conditionally applied) |

The router exposes 8 endpoints:

| Method | Path | Handler | Auth Required |
|--------|------|---------|---------------|
| `GET` | `/api/v1/health` | `handleHealth` | No |
| `POST` | `/api/v1/recommend` | `handleRecommend` | Yes |
| `POST` | `/api/v1/ingest` | `handleIngest` | Yes |
| `POST` | `/api/v1/ingest/sitemap` | `handleIngestSitemap` | Yes |
| `GET` | `/api/v1/ingest/status/{jobID}` | `handleIngestStatus` | Yes |
| `GET` | `/api/v1/ingest/result/{jobID}` | `handleIngestResult` | Yes |
| `POST` | `/api/v1/ingest/retry-dead` | `handleRetryDead` | Yes |
| `GET` | `/api/v1/link-graph` | `handleLinkGraph` | Yes |

The auth-protected endpoints are grouped in a chi `r.Group()` block. If `tokenVerifier` is `nil` (no Clerk key configured), the `RequireAuth` middleware is not attached and all endpoints are open. This supports local development without Clerk.

**CORS:** Allowed origins are parsed from the `FRONTEND_URL` config (comma-separated). Default: `http://localhost:3000` (Vite dev) and `https://autolinks-seo.vercel.app` (production). `AllowCredentials` is `false` — the frontend sends the JWT in the `Authorization` header, not via cookies.

**Error responses:** All use HTTP status codes (400 for validation, 500 for server errors, 404 for not found). Error details are sent in a `{"detail": "message"}` envelope. Internal error messages are not leaked — the `detail` field contains user-facing messages while technical details are logged server-side.

**Body size limit:** POST requests are limited to 1MB via `http.MaxBytesReader`.

### 6.10 Authentication

**Package:** `internal/auth`

The `RequireAuth` middleware:
1. Extracts the `Authorization: Bearer <token>` header
2. Calls `client.VerifyToken(token)` on the Clerk SDK
3. On success, injects the Clerk user ID into the request context under key `clerk_user_id`
4. On failure, returns `401 - {"detail": "unauthorized"}`

The `TokenVerifier` interface decouples the middleware from the specific Clerk SDK implementation. Currently the interface is satisfied by `clerk.Client` from the deprecated `clerkinc/clerk-sdk-go` package.

`UserIDFromContext(ctx)` extracts the Clerk user ID from a context — available for future use in audit logging and per-user features.

### 6.11 Data Models

**Package:** `internal/models`

All request and response types are defined as plain Go structs with JSON tags. There is no validation library — handlers validate fields manually. The types:

- `RecommendRequest` — `{text, alpha, min_similarity}`
- `IngestRequest` — `{url, content}`
- `IngestSitemapRequest` — `{sitemap_url, max_concurrent}`
- `Recommendation` — the full recommendation output with all scores
- `RecommendResponse` — `{status, latency_ms, recommendations}`
- `IngestResponse` — `{status, chunks_ingested}`
- `IngestSitemapAsyncResponse` — `{job_id, status, estimated_articles}`
- `JobStatusResponse` — `{status, progress_pct, articles_done, total, errors}`
- `JobResultResponse` — `{status, chunks_ingested, duration_seconds, errors}`
- `RetryDeadResponse` — `{retried_count, job_ids}`
- `HealthResponse` — `{status, model_loaded}`
- `LinkGraphResponse` — `{status, url_count, link_graph}`

---

## 7. Ingestion Pipeline

The recommendation engine is useless without articles indexed in Qdrant and a populated link graph. The ingestion pipeline solves this cold start problem.

### 7.1 Text Chunking

**Package:** `internal/ingest`

`ChunkText(text string, sentencesPerChunk int) []string` splits text into overlapping chunks using a sliding window.

**Sentence splitting** (`splitSentences`): A character-level scanner that splits on `. ! ?` followed by whitespace. It is deliberately simple and handles English prose correctly, though it will split on abbreviations like "Mr." or "Dr." and decimal numbers like "3.14." The tradeoff is acceptable because chunks overlap and no chunk is lost — a sentence split mid-fragment will be embedded with its surrounding context.

**Sliding window:** With `sentencesPerChunk=5` (the default used by `IngestArticle`), the stride is `sentencesPerChunk - 2 = 3`. This means chunks overlap by 2 sentences:
- Chunk 1: sentences 1-5
- Chunk 2: sentences 4-8
- Chunk 3: sentences 7-11
- ...

The overlap ensures that sentences near chunk boundaries appear in two chunks, so short or ambiguous sentences at boundaries still get context from their neighbors.

### 7.2 Sitemap Crawl and Content Extraction

The sitemap ingestion endpoint (`POST /api/v1/ingest/sitemap`) triggers a multi-phase pipeline.

**Phase 1 — Sitemap parsing** (`ParseSitemap`):

1. Fetches the sitemap XML over HTTP (10s timeout)
2. Attempts to parse as a `<sitemapindex>` first — many sites (especially WordPress with Yoast) use a sitemap index pointing to sub-sitemaps
3. If an index is found, recurses into each sub-sitemap and collects all URLs
4. If not an index, parses as a `<urlset>` with `<url>` elements containing `<loc>` tags
5. Returns the aggregated list of article URLs

**Phase 2 — Concurrent crawling** (`CrawlAndExtractBulk`):

For each URL in the sitemap, a goroutine is launched with semaphore-bounded concurrency (default: 5 simultaneous fetches). Each goroutine:

1. Acquires a semaphore slot
2. `FetchAndExtract(rawURL)` fetches the page HTML (10s timeout), strips all HTML tags with regex (`<[^>]*>`), and collapses whitespace
3. `ExtractInternalLinks(html, baseURL)` scans for `<a href="...">` tags, normalizes URLs, filters to same-domain links, excludes self-links, deduplicates, and returns sorted unique internal links
4. Returns the normalized URL, extracted text, raw HTML, and outbound links

**Phase 3 — Chunking and embedding** (per article):

`IngestArticle(url, text)`:
1. Chunks text into 5-sentence sliding windows
2. Calls `embed.EmbedBatch(chunks)` to generate embeddings for all chunks in one batch
3. `UpsertChunks(url, chunks, embeddings)`:
   - Generates deterministic point IDs using SHA-256 of `"{url}_{chunk_index}"` truncated to first 8 bytes cast to uint64
   - Converts float64 embeddings to float32
   - Constructs payload with `url`, `chunk_text`, and `chunk_index`
   - Upserts points to Qdrant with a 30-second timeout

**Phase 4 — Link graph construction** (after all articles):

`BuildLinkGraph(crawledPages)` inverts every page's outbound links into inbound counts:
1. Seeds the graph with every crawled URL at count 0
2. For each page's outbound link list, increments the target URL's count if the target is in the crawled set
3. Skips self-links (a page linking to itself)
4. Skips links to URLs not in the crawled set (external links, or links to pages not in the sitemap)
5. Logs summary statistics: total URLs, total links, matched/unmatched targets, orphan count, top inbound URLs

The resulting `map[string]int` is passed to `rerank.InitLinkGraph()` which stores it in memory and persists to Redis.

### 7.3 Link Graph Construction

The link graph is stored as `map[string]int` in memory and serialized to Redis as JSON under key `autolinks:link_graph`. The structure is:

```json
{
  "https://example.com/blog/page-a": 34,
  "https://example.com/blog/page-b": 12,
  "https://example.com/blog/page-c": 0
}
```

Each value is the count of inbound internal links to that URL from other pages within the same sitemap set. A value of 0 means no other page in the crawled set links to it — an orphan page.

**URL normalization:** Both sitemap URLs and extracted `<a href>` URLs are normalized through `NormalizeURL(rawURL)` which lowercases the scheme and host, strips trailing slashes (except for root `/`), and returns `scheme://host/path`. This ensures that `https://Example.com/blog/post/` and `http://example.com/blog/post` are treated as the same URL.

### 7.4 Async Job Queue

**Package:** `internal/jobs`

The sitemap ingestion endpoint returns immediately with a `job_id` — the actual crawl runs asynchronously in the goroutine worker pool.

**Job lifecycle:**
```
POST /ingest/sitemap → CreateJob(status: "queued") → Enqueue to WorkerPool
                                                           ↓
                                                    processJob(status: "processing")
                                                           ↓
                                          CrawlAndExtractBulk → IngestArticle → BuildLinkGraph
                                                           ↓
                                     success → UpdateJob(status: "done")
                                     failure → retry (up to 3) → DLQ → UpdateJob(status: "failed")
```

**Worker pool** (`WorkerPool`):
- 4 persistent goroutines block on a buffered channel (capacity 100)
- `Enqueue(job)` pushes a job onto the channel
- `processJobWithRetry(job)` retries up to 3 times with exponential backoff: 30s → 60s → 120s
- Each retry sets job status to `"retrying"` and sleeps before re-attempting
- After 3 failures, the job is pushed to the dead letter queue and marked `"failed"`

**Job tracking** (`CreateJob`, `GetJob`, `UpdateJob`, `AddJobError`):
- Jobs are stored in Redis as JSON under key `autolinks:job:{uuid}`
- TTL is 7 days — jobs older than 7 days are automatically removed by Redis
- `UpdateJob` does a read-modify-write cycle: GET the current JSON, merge updates, SET back
- `AddJobError` appends to the `errors` array in the job state
- Concurrent updates to the same job may race — this is known and tracked, as the Redis operations lack an atomic WATCH/MULTI/EXEC transaction guard. For the current single-worker-per-sitemap model, the risk is low since only one goroutine processes a given job at a time.

The `WorkerPool` is set on `handlers.WorkerPool` in `main.go` before the server starts. The handler checks `if WorkerPool != nil` before enqueuing — this guards against the pool being nil in tests.

### 7.5 Dead Letter Queue

When a job exhausts all retries, it is pushed to a Redis list at key `dlq:ingest`:

```json
{
  "job_id": "uuid",
  "task": "crawl_sitemap",
  "args": {"sitemap_url": "...", "max_concurrent": 5},
  "error": "no URLs found in sitemap",
  "timestamp": "2026-08-05T14:30:00Z",
  "retry_count": 3
}
```

The `POST /api/v1/ingest/retry-dead` endpoint:
1. Pops all entries from the DLQ list
2. For each entry, creates a new job with the same args
3. Enqueues the new job in the worker pool
4. Returns a count and list of the new job IDs

This allows manual inspection and reprocessing of permanently failed ingestion runs without re-submitting the sitemap URL. The `GetDLQCount()` function returns the number of pending DLQ entries for monitoring.

---

## 8. Evaluation Suite

The project includes four standalone evaluation binaries in `backend/eval/`. Each is a separate `main` package compiled independently.

### 8.1 Eval 1 — Latency

**File:** `backend/eval/latency/main.go`

**What it measures:** Round-trip time of the `/recommend` endpoint under sequential load.

**Method:**
1. Maintains a list of 10 diverse test drafts (biology, ML, quantum, climate, NLP, neuroscience, blockchain, photosynthesis, deep learning, transformers)
2. Sends 50 POST requests sequentially (cycling through the 10 drafts: 5 iterations)
3. Records `latency_ms` from each response (falls back to client-measured wall-clock time if the server doesn't report latency)
4. Computes mean, median (P50), P95, P99, min, max, and standard deviation

**Target:** Max latency under 3000ms. On warm instances the max is typically under 2000ms.

**Usage:** `go run ./eval/latency` (defaults to `http://localhost:8000/api/v1`, override with `EVAL_API_URL`)

### 8.2 Eval 2 — AI Precision (LLM-as-a-Judge)

**File:** `backend/eval/precision/main.go`

**What it measures:** Semantic accuracy of link recommendations, judged by an LLM.

**Method:**
1. Maintains a test suite of 50 drafts, drawn from Wait But Why topics (AI safety, Fermi paradox, procrastination, cognitive science, deep time, career advice, etc.)
2. A subset of drafts are flagged as `tripwire` cases — specifically designed to test edge cases where keyword matching would fail (e.g., ambiguous terms that require context)
3. For each draft, calls `/recommend` with `alpha=0.7`, `min_similarity=0.0` (the lowered threshold ensures candidates are returned even if the indexed corpus doesn't have perfect matches)
4. Each recommendation is sent to Groq's LLM API (`llama-3.3-70b-versatile`) with this prompt:

   > Given this sentence context: "{entity_context}"
   >
   > And the suggested link target page excerpt: "{target_excerpt}"
   >
   > Is this a semantically accurate and highly helpful internal link suggestion?
   >
   > Reply YES or NO only.

5. The judge evaluates the full set of qualifiers: accuracy (is the topic right?), helpfulness (would a reader benefit?), and semantic fit (does meaning match, not just keywords?)
6. Computes the YES rate across all evaluations

**Target:** >90% YES rate. The tripwire cases must also pass — a >90% overall rate with failed tripwire cases is considered a FAIL.

**Judge model:** `llama-3.3-70b-versatile` on Groq's free tier. The `GROQ_API_KEY` env var is required.

**Usage:** `go run ./eval/precision` (requires `EVAL_API_URL` and `GROQ_API_KEY`)

### 8.3 Eval 4 — Link Equity Distribution

**File:** `backend/eval/equity/main.go`

**What it measures:** How intelligently the system distributes link equity compared to a pure similarity baseline.

**Method (live mode):**
1. Fetches the current link graph from `GET /link-graph`
2. Runs 50 drafts through `/recommend` twice:
   - **Baseline:** `α = 1.0` (pure similarity, equity weighting disabled)
   - **Equity-aware:** `α = 0.7` (standard default)
3. `min_similarity` is set to `0.0` to widen the candidate pool during evaluation
4. For each configuration, the recommended URLs are tallied and projected onto the link graph (each recommendation increments the URL's count by 1)
5. Computes two metrics:
   - **Gini coefficient:** A value 0–1 measuring inequality in link distribution. 0 = every page receives equal links. 1 = one page absorbs all links. Lower is better.
   - **Orphan reduction rate:** Percentage of currently-zero-inbound-link pages that received at least one recommendation. Higher is better.

**Method (synthetic mode):**
When `--mode synthetic` is passed, a realistic synthetic link graph is generated with controlled proportions: 15% orphans (0 links), 35% low-linked (1–3 links), 30% mid-linked (4–12 links), 20% high-linked (25–80 links). Each URL type has a corresponding similarity score range (orphans score lower because they are typically niche content). The function `scoreForAlpha` simulates the same re-ranking formula used in production. This mode requires no live API and is useful for CI.

**Target:** Equity-aware Gini < Baseline Gini AND Equity-aware orphan reduction > Baseline orphan reduction. Both conditions must be true for a PASS.

**Usage:** `go run ./eval/equity --mode live` (default) or `go run ./eval/equity --mode synthetic --synthetic-urls 200 --seed 42`

---

## 9. Infrastructure and Deployment

### Service Map

| Component | Provider | Plan | URL |
|-----------|----------|------|-----|
| Frontend | Vercel | Free (Hobby) | `https://autolinks-seo.vercel.app` |
| Backend API | Render | Free (Web Service) | `https://autolinks-api.onrender.com` |
| NER + Embeddings | HuggingFace Space | Free (CPU Basic) | `eros483/autolinks-models` |
| Vector Database | Qdrant Cloud | Free (Serverless) | gRPC port 6334 |
| Link Graph + Jobs + DLQ | Upstash Redis | Free | TLS on port 6379 |
| Keepalive | GitHub Actions | Free | Every 10 min |
| **Total monthly cost** | | | **$0** |

### Free Tier Limitations and Mitigations

**Render free tier:** Web services sleep after 15 minutes of inactivity. A GitHub Actions cron job (`keepalive.yml`) pings the health endpoint every 10 minutes to prevent sleep. The cold start time is under 1 second because the Go binary is ~15MB and starts directly with no interpreter or JVM.

**HF Space free tier:** The CPU Basic plan has 16GB RAM and runs on shared hardware. Cold starts are mitigated by the keepalive ping to the HF Space health endpoint. The Gradio SSE API has serial request processing — only one request is handled at a time. This is acceptable because the Go backend batches all embeddings into a single call and all Qdrant searches run in parallel from the Go side.

**Qdrant Cloud free tier:** Limited to one collection. The Go binary checks collection existence at startup and creates it if needed, so no manual setup is required beyond providing the API key and URL.

**Upstash Redis free tier:** Limited to 256MB storage and 1000 commands per day. The link graph and job state are small (sub-MB) and command count is well within limits for this application's traffic pattern.

### Dockerfile

The backend uses a multi-stage Docker build:

**Stage 1 (build):**
- Base: `golang:1.25-alpine`
- Copies `go.mod` and `go.sum`, runs `go mod download` to cache dependencies
- Copies the entire `backend/` directory
- Builds with `CGO_ENABLED=0` (pure Go, no libc dependency) and `-ldflags="-s -w"` (strip debug info and symbol table)
- Output: a single static binary at `/server`

**Stage 2 (runtime):**
- Base: `alpine:3.21`
- Installs `ca-certificates` (for HTTPS outbound calls) and `tzdata` (for timezone support)
- Copies the binary from stage 1
- Exposes port 8000
- Entry point: `/server`

The resulting image is ~15MB. Runtime RAM is ~25MB at idle, well within Render's 512MB limit.

### Keepalive

The GitHub Actions workflow (`.github/workflows/keepalive.yml`) runs every 10 minutes and pings:
1. `https://autolinks-api.onrender.com/api/v1/health` — prevents Render sleep
2. `https://eros483-autolinks-models.hf.space/` — prevents HF Space sleep
3. Qdrant Cloud health endpoint — prevents connection pool drain

All pings use `curl -sf` (silent, fail-on-error) with generous timeouts. The `QDRANT_API_KEY` is stored as a GitHub secret.

---

## 10. Testing Strategy

### Backend Tests

Tests are co-located with source files as `*_test.go` files and use `testify/assert` for assertions and `miniredis` for Redis mocking.

**Test files and what they cover:**

| File | Package | Coverage |
|------|---------|----------|
| `extract/entities_test.go` | extract | 12 tests: entity normalization, initialism generation, deduplication, min-char filtering, empty list handling, SSE parsing (success, error, garbage), fixture matching (match/no match), dry run flow, no-URL flow |
| `embed/embeddings_test.go` | embed | 4 tests: no-URL error, batch via mock Space, single via mock Space, empty batch error |
| `rerank/rerank_test.go` | rerank | 8 tests: equity need formula, final score formula, candidate collapse, empty URL collapse, full rerank pipeline, exclusion list, empty input, link graph copy |
| `ingest/chunk_test.go` | ingest | 4 tests: basic chunking, single sentence, empty text, custom chunk size |
| `ingest/linkgraph_test.go` | ingest | 3 tests: simple graph, self-link exclusion, external link exclusion |
| `handlers/routes_test.go` | handlers | 9 tests: health, recommend-requires-text, recommend-invalid-JSON, ingest-requires-fields, sitemap-requires-URL, status-404, result-404, link-graph, retry-dead |
| `jobs/manager_test.go` | jobs | 4 tests: job creation, not-found retrieval, update, error append |
| `jobs/dlq_test.go` | jobs | 3 tests: push, pop, pop-empty |
| `auth/middleware_test.go` | auth | 5 tests: no-header, invalid-token, non-bearer, valid-token-passes-user-id, empty-token |

**Packages with no tests:** `config`, `logger`, `qdrant`, `search`, `models`, `cmd/server`

The test suite is run with `go test -race ./...` — the race detector is always enabled because the codebase uses goroutines extensively.

### Integration test approach

Handler tests use `httptest.NewRecorder` to exercise the HTTP layer without a running server. The router is created with `NewRouter(nil)` (no auth middleware), so tests bypass Clerk JWT verification. Real API calls to external services (HF Space, Qdrant) are avoided by setting env vars to trigger error paths (e.g., clearing `MODELS_SPACE_URL` to test no-URL behavior).

The embed tests use `httptest.NewServer` with a handler that mimics the Gradio Space's SSE polling protocol — POST returns an event ID, GET returns `event: complete\ndata: [...]`.

### Frontend Tests

Two test files exist:
- `utils/editor_highlight.test.js` — tests HTML escape, highlight markup generation, and phrase key encoding
- `services/api.test.js` — tests URL construction, sitemap status, and sitemap ingest payloads

Tests use Vitest. Component tests for Editor, Recommendations, Card, Header, LandingPage, and SitemapPage are not yet implemented.

### Running Tests

```bash
# Backend (all tests with race detector)
cd backend && go test -race ./...

# Frontend
cd frontend && npm run test
```

---

## 11. Configuration Reference

### Required for Production

```
# Qdrant Cloud
QDRANT_URL=https://xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx.us-west-1-0.aws.cloud.qdrant.io
QDRANT_API_KEY=your_qdrant_cloud_api_key

# HF Models Space
MODELS_SPACE_URL=https://eros483-autolinks-models.hf.space
HF_TOKEN=hf_your_huggingface_token

# Redis (Upstash)
REDIS_URL=rediss://default:password@host.upstash.io:6379

# Clerk Authentication
CLERK_SECRET_KEY=sk_test_...
VITE_CLERK_PUBLISHABLE_KEY=pk_test_...

# Frontend URL (for CORS)
FRONTEND_URL=http://localhost:3000,https://autolinks-seo.vercel.app
```

### Optional

```
PORT=8000                  # default: 8000
APP_NAME=AutoLinks         # default: AutoLinks
DEBUG=false                # default: false
DRY_RUN=false              # default: false — skips HF Space calls
RERANK_ALPHA=0.7           # default: 0.7
EMBEDDING_MODEL=all-MiniLM-L6-v2  # default
```

### Development

```bash
# Local Qdrant
docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant
QDRANT_URL=http://localhost:6334

# No external services needed
DRY_RUN=true go run ./cmd/server
# Uses hardcoded fixture entities, no HF Space, no Qdrant, no Redis required
```

---

*Last updated: 2026-08-05*

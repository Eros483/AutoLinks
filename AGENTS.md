# AGENT.md

## Project Overview
AutoLinks is a semantic internal-link generation tool for SEO teams and content publishers. It analyzes draft text, extracts named entities using GLiNER, finds semantically similar articles via Qdrant vector search, and returns link recommendations with equity-aware re-ranking that prioritizes orphan (under-linked) pages.

## Tech Stack
- Frontend: React 18 + Vite 5
- Backend: FastAPI (Python)
- Database: Qdrant (vector database, cosine similarity)
- Styling: Vanilla CSS (no framework)
- State Management: Zustand
- NER: GLiNER via pioneer.ai API
- Embeddings: all-MiniLM-L6-v2 (384-dim, SentenceTransformers)
- Content Extraction: trafilatura + BeautifulSoup4
- Evaluation Judge: Groq LLM (llama-3.3-70b-versatile)

## Key Commands

### Backend
```bash
cd backend
uv run uvicorn backend.main:app --reload        # dev server
uv run pytest                                   # run all tests
uv run pytest tests/test_api/                   # run api tests only
uv run pytest tests/test_core/                  # run core tests only
uv run pytest tests/test_eval/                  # run eval tests only
uv run black .                                  # format code
uv run pytest --cov=. --cov-report=html         # with coverage
```

### Frontend
```bash
cd frontend
npm run dev                      # dev server (port 3000)
npm run build                    # production build
npm run test                     # run tests (vitest)
npm run lint                     # lint (eslint)
```

## Directory Structure

```
AutoLinks/
├── frontend/
│   ├── src/
│   │   ├── components/          # reusable UI components (Editor, Card, Header, Layout, etc.)
│   │   ├── utils/               # helper functions (editor_highlight.js)
│   │   ├── store/               # Zustand state management (store.js)
│   │   ├── services/            # API call functions (api.js)
│   │   ├── index.css            # global styles
│   │   ├── App.jsx              # root component / view router
│   │   └── main.jsx             # entry point
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
│
├── backend/
│   ├── core/                    # business logic, domain layer (no HTTP knowledge)
│   │   ├── extract.py           # GLiNER NER entity extraction
│   │   ├── embed.py             # Sentence embedding generation (MiniLM)
│   │   ├── search.py            # Qdrant vector similarity search
│   │   ├── rerank.py            # equity-aware candidate re-ranking
│   │   └── ingest.py            # sitemap crawl, text extraction, chunking, upsert
│   ├── api/
│   │   └── v1/
│   │       └── routes.py        # versioned route handlers (thin layer)
│   ├── schemas/
│   │   ├── request.py           # Pydantic request schemas
│   │   └── response.py          # Pydantic response schemas
│   ├── utils/
│   │   ├── config.py            # Pydantic BaseSettings class, instantiated as `config`
│   │   ├── logger.py            # custom logger, imported as `logger`
│   │   └── qdrant.py            # Qdrant client initialization and collection management
│   ├── eval/
│   │   ├── eval_latency.py      # Eval 1: round-trip latency measurement (target <3s)
│   │   ├── eval_equity.py       # Eval 4: link equity distribution (Gini + orphan reduction)
│   │   └── eval_precision.py    # Eval 2: LLM-as-a-judge semantic accuracy (target >90% YES)
│   ├── tests/
│   │   ├── test_api/            # mirrors api/v1/ structure
│   │   ├── test_core/           # mirrors core/ structure
│   │   └── test_eval/           # mirrors eval/ structure
│   ├── main.py                  # FastAPI app entry point (lifespan, CORS, router)
│   ├── Dockerfile               # Docker configuration for Render deployment
│   ├── pyproject.toml           # uv project config + dependencies
│   └── requirements.txt         # pip-compatible dependency list (for Docker build)
│
├── docs/
│   ├── features.json            # canonical feature tracker — always kept up to date
│   ├── design.md                # full architecture and design document
│   ├── api.md                   # API usage documentation
│   ├── deployment.md            # deployment guide (Qdrant Cloud, Render, Vercel)
│   ├── evals.md                 # evaluation metrics documentation
│   └── frontend-design.md       # frontend design specification
├── .env.example                 # committed, no secrets
├── .gitignore
├── README.md
└── AGENT.md
```

## Conventions

### Python (Backend)
- **Package manager: `uv`** — use `uv` for all dependency management (`uv add`, `uv run`, `uv sync`). Never use `pip` directly.
- Every backend file starts with a header comment: `# ----- <4-5 word purpose> @ <file location> -----`
  - Example: `# ----- user authentication logic @ backend/core/auth.py -----`
- Formatter: black (always)
- Naming: snake_case for everything — files, variables, functions, DB columns
- Imports: sorted (isort compatible with black)
- API routes are thin: validate input → call core → return output
- core/ has zero knowledge of HTTP or FastAPI
- Env vars are accessed exclusively via the config object (`from backend.utils.config import config`) — never use `os.environ` directly.
- All logging uses the custom logger (`from backend.utils.logger import logger`) — never use `print` or the stdlib `logging` module directly.
- All imports use the full `backend.` prefix (e.g., `from backend.core import extract`).

### JavaScript (Frontend)
- camelCase for variables and functions
- PascalCase for components and types
- snake_case for file names
- All backend API calls go through `services/`, never directly in components
- API base URL is read from `VITE_API_BASE_URL` env var via `getApiBaseUrl()` in `services/api.js`

### General
- Commits: conventional commits format (feat:, fix:, chore:, docs:, test:, refactor:)
- Env vars: never committed, always have a .env.example with keys but no values
- API versioned from day one under /api/v1/
- **README badges**: READMEs should include HTML shield badges (via [shields.io](https://shields.io)) for things like build status, version, license, and tech stack. Use raw HTML `<img>` tags, not Markdown image syntax, so badge layout and alignment can be controlled.

## Development Philosophy
- TDD first: write the test, then the implementation. Never skip.
- Tests mirror the structure of the module they test
- No function ships without a test
- API routes are thin — logic lives in core/
- Explicit over clever — readable code beats smart code

## Agent Roles

This project uses a three-agent workflow. Every task goes through all three stages.

- **Planner**: breaks down the task, identifies edge cases and risks, defines what tests need to exist, produces a written plan. Writes no code. Must check /docs for any relevant design documents before planning.
- **Builder**: implements exactly per the plan — no scope creep, no improvising. Writes tests first, then implementation.
- **Reviewer**: checks correctness, black formatting, snake_case compliance, test coverage, and edge cases. Flags anything that deviates from this AGENT.md. Verifies that docs/features.json has been updated to reflect the work done.

The Planner must finish before the Builder starts.
The Reviewer must approve before any task is considered done.

## Agent Guidelines
- Always run black before considering Python code done
- Always use snake_case — no exceptions for Python files, variables, functions, DB columns
- Never modify files in /docs unless explicitly asked
- Always run tests after making changes — if tests fail, fix before moving on
- Every new backend file must start with the header comment — Reviewer should flag any file missing it
- Never use `os.environ` directly — always use `from backend.utils.config import config`
- Never use `print` or stdlib `logging` — always use `from backend.utils.logger import logger`
- Never put API calls directly in React components — they belong in services/
- Always use `uv` for Python package management — never invoke `pip` directly
- Always check /docs for relevant design documents before starting any task — if a design doc exists for what you're building, it takes precedence
- If a design doc is missing but the task is significant enough to warrant one, flag it to the user before proceeding
- Always update docs/features.json after completing any task — mark features as done, update test status, add new features if they were introduced. Follow the schema shape as defined in the existing docs/features.json.
- If something feels out of scope, flag it rather than silently doing it

## Project-Specific Notes

### External APIs
- **GLiNER / pioneer.ai**: NER entity extraction. API key stored in `PIONEER_API_KEY`. Use `DRY_RUN=true` to skip API calls during development.
- **Groq**: LLM judge for evaluation (Eval 2). API key stored in `GROQ_API_KEY`.

### Infrastructure
- **Backend**: Deployed on Render via Dockerfile. Free tier with cron-job.org keepalive. URL: `https://autolinks-api.onrender.com`
- **Frontend**: Deployed on Vercel. URL: `https://autolinks.vercel.app`
- **Vector DB**: Qdrant Cloud (free serverless tier) or local via Docker (`docker run -p 6333:6333 qdrant/qdrant`)

### Non-Standard Setup
- Backend uses `uv` (not pip). Run `uv add` to add dependencies, `uv sync` to install.
- The Python package uses namespace package structure (`backend.*` imports). The `PYTHONPATH` or working directory must include the repo root (AutoLinks/).
- Frontend `.env` lives at the repo root (not in `frontend/`). `vite.config.js` reads it from `..` via `envDir`.
- Qdrant must be running before the backend starts. The `lifespan` handler in `main.py` calls `ensure_collection()` which creates the collection if it doesn't exist.

### Files/Directories Never to Touch
- `backend/uv.lock` — managed by `uv`, never edit manually
- `frontend/package-lock.json` — managed by npm
- `frontend/dist/` — build output, never edit directly
- `logs/` — auto-generated log files
- `qdrant_storage/` — local Qdrant data directory

### Known Gotchas
- The backend module is namespaced as `backend.`. Running `uvicorn main:app --reload` from `backend/` will fail — use `uvicorn backend.main:app --reload` from the repo root, or `uv run uvicorn backend.main:app --reload` from `backend/`.
- GLiNER API responses vary in JSON structure between models. The `_normalize_entity_match()` function in `extract.py` handles multiple payload shapes.
- Qdrant has two client API surfaces (`query_points` on newer clients vs `search` on older). The `search_similar()` function in `search.py` supports both via hasattr check.
- Sitemap ingestion for large corpora (150+ articles) needs a bounded concurrency semaphore (`max_concurrent=5`) to avoid rate-limiting the source server.
- The equity eval can run in synthetic mode (`--mode synthetic`) without a live API — useful for CI/testing.
- Render free tier has a 512MB RAM limit. The sentence-transformer model (~200MB) plus the app must fit within this. No other heavy models should be loaded in-process.

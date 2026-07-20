# ----- Pydantic response schemas @ backend/schemas/response.py -----
from typing import Dict, List
from pydantic import BaseModel


class Recommendation(BaseModel):
    """Single link recommendation."""

    exact_phrase: str
    context_snippet: str
    suggested_url: str
    similarity_score: float
    equity_need_score: float
    final_score: float
    inbound_link_count: int


class RecommendResponse(BaseModel):
    """Response for /recommend endpoint."""

    status: str
    latency_ms: int
    recommendations: List[Recommendation]


class IngestResponse(BaseModel):
    """Response for /ingest endpoint."""

    status: str
    chunks_ingested: int


class IngestSitemapAsyncResponse(BaseModel):
    """Response for async /ingest/sitemap endpoint."""

    job_id: str
    status: str
    estimated_articles: int = 0


class JobStatusResponse(BaseModel):
    """Response for /ingest/status/{job_id} endpoint."""

    status: str
    progress_pct: float = 0.0
    articles_done: int = 0
    total: int = 0
    errors: List[str] = []


class JobResultResponse(BaseModel):
    """Response for /ingest/result/{job_id} endpoint."""

    status: str
    chunks_ingested: int = 0
    duration_seconds: float = 0.0
    errors: List[str] = []


class RetryDeadResponse(BaseModel):
    """Response for /ingest/retry-dead endpoint."""

    retried_count: int
    job_ids: List[str]


class HealthResponse(BaseModel):
    """Response for /health endpoint."""

    status: str
    model_loaded: bool


class LinkGraphResponse(BaseModel):
    """Response for active link graph inspection."""

    status: str
    url_count: int
    link_graph: Dict[str, int]

# ----- Pydantic response schemas @ backend/schemas/response.py -----
from typing import List, Optional
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


class HealthResponse(BaseModel):
    """Response for /health endpoint."""

    status: str
    model_loaded: bool

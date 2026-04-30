# ----- Pydantic request schemas @ backend/schemas/request.py -----
from pydantic import BaseModel, Field


class RecommendRequest(BaseModel):
    """Request body for /recommend endpoint."""

    text: str = Field(..., min_length=1, description="Draft text to analyze")
    alpha: float = Field(default=0.7, ge=0.0, le=1.0, description="Similarity weight")


class IngestRequest(BaseModel):
    """Request body for /ingest endpoint."""

    url: str = Field(..., description="Article URL")
    content: str = Field(..., min_length=1, description="Article content")


class IngestSitemapRequest(BaseModel):
    """Request body for /ingest/sitemap endpoint."""

    sitemap_url: str = Field(..., description="Sitemap URL to crawl")
    max_concurrent: int = Field(default=5, ge=1, le=20)

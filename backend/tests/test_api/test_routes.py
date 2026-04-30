# ----- API route tests @ backend/tests/test_api/test_routes.py -----
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from backend.main import app
from backend.schemas.response import RecommendResponse

client = TestClient(app)


def test_health_endpoint():
    """Test health check returns OK."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_recommend_empty_text():
    """Test that empty text returns 422 validation error."""
    response = client.post("/api/v1/recommend", json={"text": ""})
    assert response.status_code == 422


@patch("backend.core.extract.extract_entities")
@patch("backend.core.embed.embed_text")
@patch("backend.core.search.search_similar")
@patch("backend.core.rerank.rerank_candidates")
def test_recommend_returns_correct_shape(
    mock_rerank,
    mock_search,
    mock_embed,
    mock_extract,
):
    """Test recommend endpoint returns correct response shape."""
    mock_extract.return_value = [{"text": "AI", "start": 0, "end": 2, "label": "TOPIC"}]
    mock_embed.return_value = [0.1] * 384
    mock_search.return_value = [
        {
            "url": "https://example.com/ai-guide",
            "chunk_text": "AI is great",
            "score": 0.9,
        }
    ]
    mock_rerank.return_value = [
        {
            "url": "https://example.com/ai-guide",
            "chunk_text": "AI is great",
            "score": 0.9,
            "inbound_link_count": 5,
            "equity_need_score": 0.16,
            "final_score": 0.68,
        }
    ]

    response = client.post(
        "/api/v1/recommend", json={"text": "AI is changing everything"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "latency_ms" in data
    assert "recommendations" in data
    assert len(data["recommendations"]) > 0


def test_ingest_missing_fields():
    """Test that missing fields return 422."""
    response = client.post("/api/v1/ingest", json={})
    assert response.status_code == 422

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


@patch("backend.core.rerank.init_link_graph")
@patch("backend.core.ingest.ingest_article")
@patch("backend.core.ingest.build_link_graph")
@patch("backend.core.ingest.crawl_and_extract")
@patch("backend.core.ingest.parse_sitemap")
def test_ingest_sitemap_initializes_link_graph(
    mock_parse_sitemap,
    mock_crawl_and_extract,
    mock_build_link_graph,
    mock_ingest_article,
    mock_init_link_graph,
):
    """Test sitemap ingest builds and initializes the rerank link graph."""
    mock_parse_sitemap.return_value = ["https://example.com/a", "https://example.com/b"]
    mock_crawl_and_extract.return_value = {
        "https://example.com/a": {
            "text": "Article A",
            "html": "<html></html>",
            "outbound_links": ["https://example.com/b"],
        },
        "https://example.com/b": {
            "text": "Article B",
            "html": "<html></html>",
            "outbound_links": [],
        },
    }
    mock_build_link_graph.return_value = {
        "https://example.com/a": 0,
        "https://example.com/b": 1,
    }

    response = client.post(
        "/api/v1/ingest/sitemap",
        json={"sitemap_url": "https://example.com/post-sitemap.xml"},
    )

    assert response.status_code == 200
    mock_build_link_graph.assert_called_once_with(mock_crawl_and_extract.return_value)
    mock_init_link_graph.assert_called_once_with(mock_build_link_graph.return_value)
    mock_ingest_article.assert_any_call("https://example.com/a", "Article A")
    mock_ingest_article.assert_any_call("https://example.com/b", "Article B")

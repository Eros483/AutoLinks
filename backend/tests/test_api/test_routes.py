# ----- API route tests @ backend/tests/test_api/test_routes.py -----
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from backend.main import app
from backend.api.v1.routes import get_link_graph
from backend.schemas.request import RecommendRequest
from backend.schemas.response import RecommendResponse

client = TestClient(app)


def test_health_endpoint():
    """Test health check returns OK."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@patch("backend.api.v1.routes.rerank.link_graph", {"https://example.com/a": 0})
@pytest.mark.asyncio
async def test_link_graph_endpoint_returns_active_graph():
    """Test link graph endpoint exposes the server's active inbound counts."""
    response = await get_link_graph()

    assert response.status == "success"
    assert response.url_count == 1
    assert response.link_graph == {"https://example.com/a": 0}


@patch(
    "backend.api.v1.routes.rerank.link_graph",
    {
        "https://example.com/a": 8,
        "https://example.com/b": 0,
        "https://example.com/c": 1,
    },
)
@patch("backend.api.v1.routes.search.search_similar")
@patch("backend.api.v1.routes.embed.embed_text")
@patch("backend.api.v1.routes.extract.post_process_entities")
@patch("backend.api.v1.routes.extract.extract_entities")
@pytest.mark.asyncio
async def test_recommend_prefers_unique_urls_across_entities(
    mock_extract,
    mock_post_process,
    mock_embed,
    mock_search,
):
    """Test recommend widens retrieval and avoids repeating URLs across entities."""
    from backend.api.v1.routes import recommend

    entities = [
        {"text": "Entity A", "start": 0, "end": 8, "label": "TOPIC"},
        {"text": "Entity B", "start": 10, "end": 18, "label": "TOPIC"},
    ]
    mock_extract.return_value = entities
    mock_post_process.return_value = entities
    mock_embed.return_value = [0.1] * 384
    mock_search.side_effect = [
        [
            {
                "url": "https://example.com/a",
                "chunk_text": "A chunk one",
                "score": 0.95,
            },
            {
                "url": "https://example.com/a",
                "chunk_text": "A chunk two",
                "score": 0.93,
            },
            {
                "url": "https://example.com/b",
                "chunk_text": "B orphan chunk",
                "score": 0.90,
            },
        ],
        [
            {
                "url": "https://example.com/a",
                "chunk_text": "A repeated chunk",
                "score": 0.96,
            },
            {
                "url": "https://example.com/c",
                "chunk_text": "C fresh chunk",
                "score": 0.89,
            },
        ],
    ]

    response = await recommend(
        RecommendRequest(
            text="Entity A and Entity B both appear in the same draft.",
            alpha=0.7,
            min_similarity=0.65,
        )
    )

    urls = [recommendation.suggested_url for recommendation in response.recommendations]

    assert urls == [
        "https://example.com/b",
        "https://example.com/a",
        "https://example.com/c",
    ]
    assert len(urls) == len(set(urls))
    mock_search.assert_any_call([0.1] * 384, limit=100, min_score=0.65)


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
    mock_extract.return_value = [
        {"text": "Artificial Intelligence", "start": 0, "end": 23, "label": "TOPIC"}
    ]
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
        "/api/v1/recommend",
        json={"text": "Artificial Intelligence is changing everything"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "latency_ms" in data
    assert "recommendations" in data
    assert len(data["recommendations"]) > 0


@patch("backend.core.extract.extract_entities")
@patch("backend.core.embed.embed_text")
@patch("backend.core.search.search_similar")
@patch("backend.core.rerank.rerank_candidates")
@pytest.mark.asyncio
async def test_recommend_filters_entities_and_passes_min_similarity(
    mock_rerank,
    mock_search,
    mock_embed,
    mock_extract,
):
    """Test recommend drops noisy entities and forwards min_similarity to search."""
    from backend.api.v1.routes import recommend

    mock_extract.return_value = [
        {"text": "WBW", "start": 0, "end": 3, "label": "ORGANIZATION"},
        {"text": "Wait But Why", "start": 4, "end": 17, "label": "ORGANIZATION"},
        {"text": "AI", "start": 18, "end": 20, "label": "TOPIC"},
    ]
    mock_embed.return_value = [0.1] * 384
    mock_search.return_value = [
        {
            "url": "https://example.com/wait-but-why",
            "chunk_text": "Wait But Why article",
            "score": 0.72,
        }
    ]
    mock_rerank.return_value = [
        {
            "url": "https://example.com/wait-but-why",
            "chunk_text": "Wait But Why article",
            "score": 0.72,
            "inbound_link_count": 2,
            "equity_need_score": 0.33,
            "final_score": 0.6,
        }
    ]

    response = await recommend(
        RecommendRequest(
            text="Wait But Why is hosting a gathering.",
            alpha=0.7,
            min_similarity=0.65,
        )
    )

    assert response.status == "success"
    assert len(response.recommendations) == 1
    mock_embed.assert_called_once()
    mock_search.assert_called_once_with([0.1] * 384, limit=100, min_score=0.65)


def test_ingest_missing_fields():
    """Test that missing fields return 422."""
    response = client.post("/api/v1/ingest", json={})
    assert response.status_code == 422


@patch("backend.core.tasks.crawl_and_ingest_task.delay")
@patch("backend.core.jobs.create_job")
@patch("backend.core.ingest.parse_sitemap")
def test_ingest_sitemap_enqueues_job(
    mock_parse_sitemap,
    mock_create_job,
    mock_delay,
):
    """Test sitemap ingest enqueues a background job and returns job_id."""
    mock_parse_sitemap.return_value = ["https://example.com/a", "https://example.com/b"]
    mock_create_job.return_value = "test-job-uuid-123"

    response = client.post(
        "/api/v1/ingest/sitemap",
        json={"sitemap_url": "https://example.com/post-sitemap.xml"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == "test-job-uuid-123"
    assert data["status"] == "queued"
    assert data["estimated_articles"] == 2

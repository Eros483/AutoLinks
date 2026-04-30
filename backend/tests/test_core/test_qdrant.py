# ----- Qdrant client behavior tests @ backend/tests/test_core/test_qdrant.py -----
from types import SimpleNamespace
from unittest.mock import MagicMock

from backend.core import search


def test_create_qdrant_client_uses_local_url_without_api_key(monkeypatch):
    """Test local Qdrant config does not pass an empty API key."""
    captured_kwargs = {}

    def fake_client(**kwargs):
        captured_kwargs.update(kwargs)
        return object()

    from backend.utils.qdrant import create_qdrant_client
    from backend.utils import qdrant

    monkeypatch.setattr(
        qdrant, "qdrant_client", SimpleNamespace(QdrantClient=fake_client)
    )
    monkeypatch.setattr(qdrant.config, "qdrant_url", "http://localhost:6333")
    monkeypatch.setattr(qdrant.config, "qdrant_api_key", "")

    create_qdrant_client()

    assert captured_kwargs == {"url": "http://localhost:6333"}


def test_create_qdrant_client_includes_api_key_when_present(monkeypatch):
    """Test hosted Qdrant config still passes the API key."""
    captured_kwargs = {}

    def fake_client(**kwargs):
        captured_kwargs.update(kwargs)
        return object()

    from backend.utils.qdrant import create_qdrant_client
    from backend.utils import qdrant

    monkeypatch.setattr(
        qdrant, "qdrant_client", SimpleNamespace(QdrantClient=fake_client)
    )
    monkeypatch.setattr(qdrant.config, "qdrant_url", "https://example.qdrant.io")
    monkeypatch.setattr(qdrant.config, "qdrant_api_key", "secret-key")

    create_qdrant_client()

    assert captured_kwargs == {
        "url": "https://example.qdrant.io",
        "api_key": "secret-key",
    }


def test_search_similar_returns_normalized_results(monkeypatch):
    """Test Qdrant search results are mapped into the public shape."""
    mock_client = MagicMock()
    mock_client.search.return_value = [
        SimpleNamespace(
            score=0.91,
            payload={
                "url": "https://example.com/post",
                "chunk_text": "Example chunk",
            },
        )
    ]

    monkeypatch.setattr(search, "get_qdrant_client", lambda: mock_client)
    monkeypatch.setattr(search.config, "qdrant_collection", "articles")

    results = search.search_similar([0.1, 0.2, 0.3], limit=5, min_score=0.7)

    assert results == [
        {
            "url": "https://example.com/post",
            "chunk_text": "Example chunk",
            "score": 0.91,
        }
    ]
    mock_client.search.assert_called_once_with(
        collection_name="articles",
        query_vector=[0.1, 0.2, 0.3],
        limit=5,
        score_threshold=0.7,
    )

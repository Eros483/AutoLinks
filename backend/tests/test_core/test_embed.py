# ----- Embedding and chunking tests @ backend/tests/test_core/test_embed.py -----
import json

import httpx

from backend.core.embed import embed_text, embed_batch
from backend.core.ingest import chunk_text


def test_embed_text_via_space_returns_list(monkeypatch):
    captured_calls = []

    def mock_post(url, json=None, headers=None, timeout=None):
        captured_calls.append(("post", url, json))
        request = httpx.Request("POST", url)
        return httpx.Response(200, request=request, json={"event_id": "emb-1"})

    def mock_get(url, headers=None, timeout=None):
        embedding = [[0.1, 0.2, 0.3]]
        sse = f"event: complete\ndata: [{json.dumps(json.dumps(embedding))}]\n"
        request = httpx.Request("GET", url)
        return httpx.Response(200, request=request, text=sse)

    monkeypatch.setattr("backend.core.extract.httpx.post", mock_post)
    monkeypatch.setattr("backend.core.extract.httpx.get", mock_get)
    monkeypatch.setattr(
        "backend.core.embed.config.models_space_url",
        "https://eros483-autolinks-models.hf.space",
    )
    monkeypatch.setattr("backend.core.embed.config.hf_token", "")

    result = embed_text("test sentence")

    assert isinstance(result, list)
    assert len(result) == 3
    assert all(isinstance(x, float) for x in result)


def test_embed_batch_via_space(monkeypatch):
    def mock_post(url, json=None, headers=None, timeout=None):
        request = httpx.Request("POST", url)
        return httpx.Response(200, request=request, json={"event_id": "emb-2"})

    def mock_get(url, headers=None, timeout=None):
        embeddings = [[0.1, 0.2], [0.3, 0.4]]
        sse = f"event: complete\ndata: [{json.dumps(json.dumps(embeddings))}]\n"
        request = httpx.Request("GET", url)
        return httpx.Response(200, request=request, text=sse)

    monkeypatch.setattr("backend.core.extract.httpx.post", mock_post)
    monkeypatch.setattr("backend.core.extract.httpx.get", mock_get)
    monkeypatch.setattr(
        "backend.core.embed.config.models_space_url",
        "https://eros483-autolinks-models.hf.space",
    )

    results = embed_batch(["text one", "text two"])

    assert len(results) == 2
    assert results[0] == [0.1, 0.2]
    assert results[1] == [0.3, 0.4]


def test_embed_text_falls_back_to_local_when_no_space_url(monkeypatch):
    monkeypatch.setattr("backend.core.embed.config.models_space_url", "")

    result = embed_text("test sentence")

    assert isinstance(result, list)
    assert len(result) > 0
    assert all(isinstance(x, float) for x in result)


def test_embed_text_deterministic_local(monkeypatch):
    monkeypatch.setattr("backend.core.embed.config.models_space_url", "")

    result1 = embed_text("deterministic test")
    result2 = embed_text("deterministic test")

    assert result1 == result2


def test_chunk_text_basic():
    text = "First sentence. Second sentence. Third sentence. Fourth sentence. Fifth sentence."
    chunks = chunk_text(text, sentences_per_chunk=3)
    assert len(chunks) >= 1


def test_chunk_text_preserves_content():
    text = "This is a test sentence. Another sentence here. More content."
    chunks = chunk_text(text)
    combined = " ".join(chunks)
    assert "test sentence" in combined.lower()


def test_chunk_text_empty_input():
    assert chunk_text("") == []


def test_chunk_text_short_input():
    chunks = chunk_text("Short text.")
    assert len(chunks) >= 1

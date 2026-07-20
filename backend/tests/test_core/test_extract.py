# ----- entity extraction tests @ backend/tests/test_core/test_extract.py -----
import json

import httpx
import pytest

from backend.core.extract import (
    extract_entities,
    post_process_entities,
    _call_space,
    _parse_sse_data,
)


def test_extract_entities_calls_space_and_parses_response(monkeypatch):
    captured_requests = []

    def mock_post(url, json=None, headers=None, timeout=None):
        captured_requests.append(("post", url, json, headers))
        request = httpx.Request("POST", url)
        return httpx.Response(
            200,
            request=request,
            json={"event_id": "test-event-123"},
        )

    def mock_get(url, headers=None, timeout=None):
        captured_requests.append(("get", url, headers))
        request = httpx.Request("GET", url)
        entities = [
            {
                "text": "CUDA optimization",
                "start": 12,
                "end": 29,
                "label": "TECHNOLOGY",
            },
            {"text": "gradient descent", "start": 0, "end": 16, "label": "CONCEPT"},
        ]
        sse_body = "event: complete\ndata: [{}]\n".format(
            json.dumps(json.dumps(entities))
        )
        return httpx.Response(200, request=request, text=sse_body)

    monkeypatch.setattr("backend.core.extract.httpx.post", mock_post)
    monkeypatch.setattr("backend.core.extract.httpx.get", mock_get)
    monkeypatch.setattr("backend.core.extract.config.dry_run", False)
    monkeypatch.setattr(
        "backend.core.extract.config.models_space_url",
        "https://eros483-autolinks-models.hf.space",
    )
    monkeypatch.setattr("backend.core.extract.config.hf_token", "test-token")

    entities = extract_entities("CUDA optimization improves gradient descent.")

    assert len(captured_requests) == 2

    assert captured_requests[0][0] == "post"
    post_url = captured_requests[0][1]
    assert "/gradio_api/call/extract_entities" in post_url
    assert captured_requests[0][3]["Authorization"] == "Bearer test-token"

    assert entities == [
        {"text": "CUDA optimization", "start": 12, "end": 29, "label": "TECHNOLOGY"},
        {"text": "gradient descent", "start": 0, "end": 16, "label": "CONCEPT"},
    ]


def test_extract_entities_raises_on_space_error(monkeypatch):
    def mock_post(url, json=None, headers=None, timeout=None):
        request = httpx.Request("POST", url)
        return httpx.Response(200, request=request, json={"event_id": "test-event-err"})

    def mock_get(url, headers=None, timeout=None):
        request = httpx.Request("GET", url)
        sse_body = 'event: error\ndata: {"error": "ZeroGPU quota exceeded", "title": "Error"}\n'
        return httpx.Response(200, request=request, text=sse_body)

    monkeypatch.setattr("backend.core.extract.httpx.post", mock_post)
    monkeypatch.setattr("backend.core.extract.httpx.get", mock_get)
    monkeypatch.setattr("backend.core.extract.config.dry_run", False)
    monkeypatch.setattr(
        "backend.core.extract.config.models_space_url",
        "https://eros483-autolinks-models.hf.space",
    )

    try:
        extract_entities("Test text")
        assert False, "Expected RuntimeError"
    except RuntimeError as e:
        assert "ZeroGPU quota exceeded" in str(e)


def test_extract_entities_uses_dry_run_fixtures(monkeypatch):
    monkeypatch.setattr("backend.core.extract.config.dry_run", True)

    entities = extract_entities("CUDA optimization improves gradient descent.")

    assert len(entities) == 2
    assert entities[0]["text"] == "CUDA optimization"
    assert entities[1]["text"] == "gradient descent"


def test_parse_sse_data_complete():
    entities = [{"text": "test", "start": 0, "end": 4, "label": "TOPIC"}]
    sse = "event: complete\ndata: [{}]\n".format(json.dumps(json.dumps(entities)))

    result = _parse_sse_data(sse)

    assert json.loads(result) == entities


def test_parse_sse_data_error():
    sse = 'event: error\ndata: {"error": "something broke", "title": "Error"}\n'

    with pytest.raises(RuntimeError, match="something broke"):
        _parse_sse_data(sse)


def test_post_process_entities_filters_short_and_initialism_duplicates():
    entities = [
        {"text": "WBW", "start": 0, "end": 3, "label": "ORGANIZATION"},
        {"text": "Wait But Why", "start": 5, "end": 18, "label": "ORGANIZATION"},
        {"text": "king of spades", "start": 20, "end": 34, "label": "TOPIC"},
        {"text": "AI", "start": 36, "end": 38, "label": "TOPIC"},
        {"text": "Wait But Hi", "start": 40, "end": 51, "label": "ORGANIZATION"},
        {"text": "WBH", "start": 53, "end": 56, "label": "ORGANIZATION"},
    ]

    processed = post_process_entities(entities, min_char_length=5)

    assert processed == [
        {"text": "Wait But Why", "start": 5, "end": 18, "label": "ORGANIZATION"},
        {"text": "king of spades", "start": 20, "end": 34, "label": "TOPIC"},
        {"text": "Wait But Hi", "start": 40, "end": 51, "label": "ORGANIZATION"},
    ]

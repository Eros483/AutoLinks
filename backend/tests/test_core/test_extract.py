# ----- entity extraction tests @ backend/tests/test_core/test_extract.py -----
import json

import httpx

from backend.core.extract import (
    _normalize_entity_match,
    extract_entities,
    post_process_entities,
)


def test_extract_entities_calls_pioneer_and_normalizes_response(monkeypatch):
    """Test Pioneer NER call payload and response normalization."""

    captured_request = {}

    def mock_post(url, json=None, headers=None, timeout=None):
        captured_request["url"] = url
        captured_request["json"] = json
        captured_request["headers"] = headers
        captured_request["timeout"] = timeout

        request = httpx.Request("POST", url)
        return httpx.Response(
            200,
            request=request,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json_module.dumps(
                                {
                                    "entities": {
                                        "technology": [
                                            {
                                                "text": "CUDA optimization",
                                                "start": 12,
                                                "end": 29,
                                            }
                                        ],
                                        "concept": ["gradient descent"],
                                    }
                                }
                            )
                        }
                    }
                ]
            },
        )

    json_module = json
    monkeypatch.setattr("backend.core.extract.httpx.post", mock_post)
    monkeypatch.setattr("backend.core.extract.config.dry_run", False)
    monkeypatch.setattr("backend.core.extract.config.pioneer_api_key", "test-key")
    monkeypatch.setattr(
        "backend.core.extract.config.gliner_url",
        "https://api.pioneer.ai/v1/chat/completions",
    )

    entities = extract_entities("CUDA optimization improves gradient descent.")

    assert captured_request["url"] == "https://api.pioneer.ai/v1/chat/completions"
    assert captured_request["headers"]["Authorization"] == "Bearer test-key"
    assert captured_request["timeout"] == 30.0
    assert captured_request["json"]["model"] == "fastino/gliner2-base-v1"
    assert captured_request["json"]["include_spans"] is True
    assert captured_request["json"]["messages"] == [
        {
            "role": "user",
            "content": "CUDA optimization improves gradient descent.",
        }
    ]
    assert entities == [
        {
            "text": "CUDA optimization",
            "start": 12,
            "end": 29,
            "label": "TECHNOLOGY",
        },
        {
            "text": "gradient descent",
            "start": 0,
            "end": 16,
            "label": "CONCEPT",
        },
    ]


def test_extract_entities_supports_nested_data_entities_payload(monkeypatch):
    """Test Pioneer responses nested under data.entities still parse correctly."""
    json_module = json

    def mock_post(url, json=None, headers=None, timeout=None):
        request = httpx.Request("POST", url)
        return httpx.Response(
            200,
            request=request,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json_module.dumps(
                                {
                                    "data": {
                                        "entities": {
                                            "organization": [
                                                {
                                                    "text": "OpenAI",
                                                    "start": 0,
                                                    "end": 6,
                                                }
                                            ]
                                        }
                                    }
                                }
                            )
                        }
                    }
                ]
            },
        )

    monkeypatch.setattr("backend.core.extract.httpx.post", mock_post)
    monkeypatch.setattr("backend.core.extract.config.dry_run", False)
    monkeypatch.setattr("backend.core.extract.config.pioneer_api_key", "test-key")

    entities = extract_entities("OpenAI released a model.")

    assert entities == [
        {
            "text": "OpenAI",
            "start": 0,
            "end": 6,
            "label": "ORGANIZATION",
        }
    ]


def test_extract_entities_raises_http_error(monkeypatch):
    """Test Pioneer HTTP failures are surfaced to callers."""

    def mock_post(url, json=None, headers=None, timeout=None):
        request = httpx.Request("POST", url)
        response = httpx.Response(401, request=request)
        raise httpx.HTTPStatusError(
            "Unauthorized",
            request=request,
            response=response,
        )

    monkeypatch.setattr("backend.core.extract.httpx.post", mock_post)
    monkeypatch.setattr("backend.core.extract.config.dry_run", False)
    monkeypatch.setattr("backend.core.extract.config.pioneer_api_key", "bad-key")

    try:
        extract_entities("Test text")
        assert False, "Expected httpx.HTTPError to be raised"
    except httpx.HTTPError:
        pass


def test_normalize_entity_match_handles_dict_payload():
    """Test Pioneer dict entities are normalized into response-safe strings."""
    normalized = _normalize_entity_match(
        {"text": "WBW readers", "start": 135, "end": 146},
        "organization",
    )

    assert normalized == {
        "text": "WBW readers",
        "start": 135,
        "end": 146,
        "label": "ORGANIZATION",
    }


def test_post_process_entities_filters_short_and_initialism_duplicates():
    """Test entity post-processing removes noisy short tokens and initials duplicates."""
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

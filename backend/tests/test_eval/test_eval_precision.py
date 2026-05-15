# ----- precision evaluation tests @ backend/tests/test_eval/test_eval_precision.py -----
import httpx

from backend.eval.eval_precision import (
    build_judge_messages,
    judge_recommendation,
    parse_judge_response,
)


def test_build_judge_messages_includes_source_and_target_context():
    """Test judge prompt contains the source context and recommendation details."""
    recommendation = {
        "exact_phrase": "CUDA optimization",
        "context_snippet": "GPU profiling and CUDA optimization can reduce bottlenecks.",
        "suggested_url": "https://example.com/gpu-guide",
    }

    messages = build_judge_messages(
        "CUDA optimization improved our training loop latency.",
        recommendation,
    )

    assert messages[0]["role"] == "system"
    assert "Return strict JSON" in messages[0]["content"]
    assert (
        "CUDA optimization improved our training loop latency."
        in messages[1]["content"]
    )
    assert "https://example.com/gpu-guide" in messages[1]["content"]


def test_parse_judge_response_accepts_json_string_payload():
    """Test Groq JSON-mode content parses into a stable verdict object."""
    verdict = parse_judge_response(
        '{"verdict":"YES","rationale":"The target snippet clearly matches the draft topic."}'
    )

    assert verdict == {
        "verdict": "YES",
        "rationale": "The target snippet clearly matches the draft topic.",
    }


def test_judge_recommendation_calls_groq_and_parses_verdict(monkeypatch):
    """Test judge request payload and response parsing against Groq format."""
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
                            "content": '{"verdict":"NO","rationale":"The snippet does not match the source meaning."}'
                        }
                    }
                ]
            },
        )

    monkeypatch.setattr("backend.eval.eval_precision.httpx.post", mock_post)
    monkeypatch.setattr("backend.eval.eval_precision.config.groq_api_key", "groq-test")
    monkeypatch.setattr(
        "backend.eval.eval_precision.config.groq_url",
        "https://api.groq.com/openai/v1/chat/completions",
    )
    monkeypatch.setattr(
        "backend.eval.eval_precision.config.groq_model",
        "llama-3.3-70b-versatile",
    )

    verdict = judge_recommendation(
        "Elon Musk founded SpaceX and later launched Neuralink.",
        {
            "exact_phrase": "Neuralink",
            "context_snippet": "Neuralink is a brain-computer interface company.",
            "suggested_url": "https://example.com/neuralink",
        },
    )

    assert captured_request["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert captured_request["headers"]["Authorization"] == "Bearer groq-test"
    assert captured_request["json"]["response_format"] == "json"
    assert captured_request["json"]["temperature"] == 0
    assert verdict == {
        "verdict": "NO",
        "rationale": "The snippet does not match the source meaning.",
    }

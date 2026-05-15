# ----- precision evaluation tests @ backend/tests/test_eval/test_eval_precision.py -----
from backend.eval.eval_precision import (
    build_judge_messages,
    build_judge_response_format,
    judge_recommendation,
    parse_judge_response,
)


def test_build_judge_messages_includes_source_and_target_context():
    """Test judge prompt contains richer source and target context."""
    recommendation = {
        "exact_phrase": "CUDA optimization",
        "context_snippet": "GPU profiling and CUDA optimization can reduce bottlenecks.",
        "suggested_url": "https://example.com/gpu-guide",
    }

    messages = build_judge_messages(
        "CUDA optimization improved our training loop latency.",
        recommendation,
        target_page_excerpt="This article explains CUDA kernels, memory pressure, and profiling strategy.",
    )

    assert messages[0]["role"] == "system"
    assert "semantic precision" in messages[0]["content"]
    assert "Source focus excerpt" in messages[1]["content"]
    assert "https://example.com/gpu-guide" in messages[1]["content"]
    assert "Additional target-page excerpt" in messages[1]["content"]


def test_build_judge_response_format_uses_strict_schema_for_supported_models():
    """Test supported Groq models use strict JSON schema mode."""
    response_format = build_judge_response_format("openai/gpt-oss-20b")

    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["strict"] is True


def test_build_judge_response_format_uses_json_object_for_llama_models():
    """Test non-strict models fall back to JSON object mode."""
    response_format = build_judge_response_format("llama-3.3-70b-versatile")

    assert response_format == {"type": "json_object"}


def test_parse_judge_response_accepts_json_string_payload():
    """Test Groq JSON content parses into a stable verdict object."""
    verdict = parse_judge_response(
        '{"verdict":"YES","rationale":"The target snippet clearly matches the draft topic."}'
    )

    assert verdict == {
        "verdict": "YES",
        "rationale": "The target snippet clearly matches the draft topic.",
    }


def test_judge_recommendation_calls_groq_sdk_and_parses_verdict(monkeypatch):
    """Test SDK request payload and response parsing against Groq format."""
    captured_request = {}

    class FakeCompletions:
        def create(self, **kwargs):
            captured_request.update(kwargs)

            class FakeMessage:
                content = '{"verdict":"NO","rationale":"The snippet does not match the source meaning."}'

            class FakeChoice:
                message = FakeMessage()

            class FakeResponse:
                choices = [FakeChoice()]

            return FakeResponse()

    class FakeChat:
        completions = FakeCompletions()

    class FakeGroqClient:
        chat = FakeChat()

    monkeypatch.setattr(
        "backend.eval.eval_precision.config.groq_model",
        "llama-3.3-70b-versatile",
    )

    verdict = judge_recommendation(
        FakeGroqClient(),
        "Elon Musk founded SpaceX and later launched Neuralink.",
        {
            "exact_phrase": "Neuralink",
            "context_snippet": "Neuralink is a brain-computer interface company.",
            "suggested_url": "https://example.com/neuralink",
        },
        target_page_excerpt="Neuralink develops implantable brain-computer interfaces.",
    )

    assert captured_request["model"] == "llama-3.3-70b-versatile"
    assert captured_request["temperature"] == 0
    assert captured_request["response_format"]["type"] == "json_object"
    assert verdict == {
        "verdict": "NO",
        "rationale": "The snippet does not match the source meaning.",
    }

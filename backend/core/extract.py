# ----- NER entity extraction via HF Space @ backend/core/extract.py -----
import json
import re
from typing import List, Dict, Any

import httpx

from backend.utils.config import config
from backend.utils.logger import logger

DEFAULT_ENTITY_LABELS = [
    "person",
    "organization",
    "topic",
    "technology",
    "concept",
]


def extract_entities(text: str) -> List[Dict[str, Any]]:
    """
    Extract named entities from text using GLiNER2 on HF Space.

    Args:
        text: Raw draft text to analyze

    Returns:
        List of entity dicts with text, start, end, and label
    """
    if config.dry_run:
        logger.info("DRY_RUN enabled, returning fixture entities")
        return _get_fixture_entities(text)

    if not config.models_space_url:
        logger.warning("models_space_url not configured, returning empty")
        return []

    labels_json = json.dumps(DEFAULT_ENTITY_LABELS)
    result = _call_space("extract_entities", text, labels_json)
    entities = json.loads(result)

    logger.info("Extracted %d entities from text", len(entities))
    return entities


def post_process_entities(
    entities: List[Dict[str, Any]], min_char_length: int = 5
) -> List[Dict[str, Any]]:
    """Filter noisy entities and remove duplicates before vector search."""
    filtered_entities = []
    initialisms = set()

    for entity in entities:
        entity_text = entity.get("text", "").strip()
        normalized_text = _normalize_entity_text(entity_text)
        if len(normalized_text) < min_char_length:
            continue

        initialism = _to_initialism(entity_text)
        if initialism:
            initialisms.add(initialism)

        filtered_entities.append(
            {
                **entity,
                "text": entity_text,
            }
        )

    deduplicated_entities = []
    seen_normalized_text = set()
    for entity in filtered_entities:
        normalized_text = _normalize_entity_text(entity["text"])
        if normalized_text in seen_normalized_text:
            continue
        if normalized_text.isalpha() and normalized_text in initialisms:
            continue

        seen_normalized_text.add(normalized_text)
        deduplicated_entities.append(entity)

    logger.info(
        "Post-processed entities from %d to %d",
        len(entities),
        len(deduplicated_entities),
    )
    return deduplicated_entities


def _call_space(endpoint: str, *args: str) -> str:
    """Call a Gradio Space endpoint and return the JSON string result."""
    headers = {"Content-Type": "application/json"}
    if config.hf_token:
        headers["Authorization"] = f"Bearer {config.hf_token}"

    url = f"{config.models_space_url}/gradio_api/call/{endpoint}"

    response = httpx.post(
        url,
        json={"data": list(args)},
        headers=headers,
        timeout=60.0,
    )
    response.raise_for_status()
    event_id = response.json()["event_id"]

    result_url = f"{url}/{event_id}"
    result_text = _poll_result(result_url, headers)

    return _parse_sse_data(result_text)


def _poll_result(url: str, headers: dict) -> str:
    """Poll the event result URL with exponential backoff until completion."""
    import time

    delay = 0.5
    max_attempts = 30

    for attempt in range(max_attempts):
        resp = httpx.get(url, headers=headers, timeout=30.0)
        resp.raise_for_status()
        text = resp.text

        if "event: complete" in text or "event: error" in text:
            return text

        if attempt == 0:
            logger.info("Waiting for Space result (endpoint: %s)", url)
        time.sleep(delay)
        delay = min(delay * 1.5, 5.0)

    raise RuntimeError(f"Timeout waiting for Space result: {url}")


def _parse_sse_data(sse_text: str) -> str:
    """Extract the JSON string from SSE event: complete response."""
    if "event: error" in sse_text:
        for line in sse_text.split("\n"):
            if line.startswith("data:"):
                error_data = json.loads(line[5:].strip())
                raise RuntimeError(f"Space error: {error_data.get('error', 'unknown')}")

    for line in sse_text.split("\n"):
        if line.startswith("data:"):
            data_str = line[5:].strip()
            return json.loads(data_str)[0]

    raise RuntimeError(f"Unexpected SSE response: {sse_text[:200]}")


def _get_fixture_entities(text: str) -> List[Dict[str, Any]]:
    """Return hardcoded entities for development without API calls."""
    fixtures = [
        {"text": "CUDA optimization", "start": 10, "end": 26, "label": "TECHNOLOGY"},
        {"text": "spatial computing", "start": 50, "end": 66, "label": "TECHNOLOGY"},
        {"text": "gradient descent", "start": 100, "end": 115, "label": "CONCEPT"},
    ]
    return [f for f in fixtures if f["text"].lower() in text.lower()]


def _normalize_entity_text(text: str) -> str:
    """Normalize entity text for deduplication comparisons."""
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def _to_initialism(text: str) -> str:
    """Convert a multi-word entity into its lowercase initialism."""
    words = re.findall(r"[A-Za-z0-9]+", text)
    if len(words) < 2:
        return ""

    return "".join(word[0].lower() for word in words)

# ----- NER entity extraction @ backend/core/extract.py -----
from typing import List, Dict, Any

import httpx

from backend.utils.config import config
from backend.utils.logger import logger


def extract_entities(text: str) -> List[Dict[str, Any]]:
    """
    Extract named entities from text using GLiNER via Pioneer API.

    Args:
        text: Raw draft text to analyze

    Returns:
        List of entity dicts with text, start, end, and label
    """
    if config.dry_run:
        logger.info("DRY_RUN enabled, returning fixture entities")
        return _get_fixture_entities(text)

    headers = {
        "Authorization": f"Bearer {config.pioneer_api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "fastino/gliner2-base-v1",
        "messages": [{"role": "user", "content": text}],
        "schema": {
            "entities": ["person", "organization", "topic", "technology", "concept"]
        },
        "include_spans": True,
    }

    try:
        response = httpx.post(
            config.gliner_url, json=payload, headers=headers, timeout=30.0
        )
        response.raise_for_status()
        result = response.json()

        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        if isinstance(content, str):
            import json

            content = json.loads(content)

        entities_map = content.get("entities", {})
        results = []
        for label, matches in entities_map.items():
            for match in matches:
                normalized_match = _normalize_entity_match(match, label)
                if normalized_match["text"]:
                    results.append(normalized_match)

        logger.info(f"Extracted {len(results)} entities from text")
        return results

    except httpx.HTTPError as e:
        logger.error(f"Pioneer API error: {e}")
        raise


def _get_fixture_entities(text: str) -> List[Dict[str, Any]]:
    """Return hardcoded entities for development without API calls."""
    fixtures = [
        {"text": "CUDA optimization", "start": 10, "end": 26, "label": "TECHNOLOGY"},
        {"text": "spatial computing", "start": 50, "end": 66, "label": "TECHNOLOGY"},
        {"text": "gradient descent", "start": 100, "end": 115, "label": "CONCEPT"},
    ]
    return [f for f in fixtures if f["text"].lower() in text.lower()]


def _normalize_entity_match(match: Any, label: str) -> Dict[str, Any]:
    """Normalize Pioneer entity payloads into a consistent internal shape."""
    if isinstance(match, str):
        return {
            "text": match,
            "start": 0,
            "end": len(match),
            "label": label.upper(),
        }

    if isinstance(match, dict):
        entity_text = (
            match.get("text")
            or match.get("value")
            or match.get("entity")
            or match.get("span")
            or ""
        )
        start = match.get("start", 0)
        end = match.get("end", start + len(entity_text))

        return {
            "text": entity_text,
            "start": start,
            "end": end,
            "label": label.upper(),
        }

    return {"text": "", "start": 0, "end": 0, "label": label.upper()}

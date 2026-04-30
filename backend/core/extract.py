# ----- NER entity extraction @ backend/core/extract.py -----
from typing import List, Dict, Any
import httpx
from backend.utils.config import config
from backend.utils.logger import logger


def extract_entities(text: str) -> List[Dict[str, Any]]:
    """
    Extract named entities from text using GLiNER API.

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
        "model": config.gliner_model,
        "text": text,
        "labels": ["PERSON", "ORGANIZATION", "TOPIC", "TECHNOLOGY", "CONCEPT"],
    }

    try:
        response = httpx.post(
            config.gliner_url, json=payload, headers=headers, timeout=30.0
        )
        response.raise_for_status()
        data = response.json()

        entities = []
        for item in data.get("results", []):
            entities.append(
                {
                    "text": item.get("text", ""),
                    "start": item.get("span", {}).get("start", 0),
                    "end": item.get("span", {}).get("end", 0),
                    "label": item.get("label", "UNKNOWN"),
                }
            )

        logger.info(f"Extracted {len(entities)} entities from text")
        return entities

    except httpx.HTTPError as e:
        logger.error(f"GLiNER API error: {e}")
        raise


def _get_fixture_entities(text: str) -> List[Dict[str, Any]]:
    """Return hardcoded entities for development without API calls."""
    fixtures = [
        {"text": "CUDA optimization", "start": 10, "end": 26, "label": "TECHNOLOGY"},
        {"text": "spatial computing", "start": 50, "end": 66, "label": "TECHNOLOGY"},
        {"text": "gradient descent", "start": 100, "end": 115, "label": "CONCEPT"},
    ]
    return [f for f in fixtures if f["text"].lower() in text.lower()]

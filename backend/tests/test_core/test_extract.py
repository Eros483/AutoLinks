# ----- entity extraction tests @ backend/tests/test_core/test_extract.py -----
from backend.core.extract import _normalize_entity_match, post_process_entities


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

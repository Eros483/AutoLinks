# ----- entity extraction tests @ backend/tests/test_core/test_extract.py -----
from backend.core.extract import _normalize_entity_match


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

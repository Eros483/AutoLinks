# ----- Embedding and chunking tests @ backend/tests/test_core/test_embed.py -----
import pytest
from backend.core.embed import embed_text
from backend.core.ingest import chunk_text


def test_embed_text_returns_list():
    """Test that embed_text returns a list of floats."""
    result = embed_text("test sentence")
    assert isinstance(result, list)
    assert len(result) > 0
    assert all(isinstance(x, float) for x in result)


def test_embed_text_deterministic():
    """Test that same text produces same embedding."""
    result1 = embed_text("deterministic test")
    result2 = embed_text("deterministic test")
    assert result1 == result2


def test_chunk_text_basic():
    """Test basic chunking produces expected number of chunks."""
    text = "First sentence. Second sentence. Third sentence. Fourth sentence. Fifth sentence."
    chunks = chunk_text(text, sentences_per_chunk=3)
    assert len(chunks) >= 1


def test_chunk_text_preserves_content():
    """Test that chunked text contains original content."""
    text = "This is a test sentence. Another sentence here. More content."
    chunks = chunk_text(text)
    combined = " ".join(chunks)
    assert "test sentence" in combined.lower()


def test_chunk_text_empty_input():
    """Test that empty text returns empty list."""
    assert chunk_text("") == []


def test_chunk_text_short_input():
    """Test that very short text still returns at least one chunk."""
    chunks = chunk_text("Short text.")
    assert len(chunks) >= 1

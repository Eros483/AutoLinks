# ----- Re-ranking logic tests @ backend/tests/test_core/test_rerank.py -----
import pytest
from backend.core.rerank import (
    collapse_candidates_by_url,
    equity_need,
    final_score,
    rerank_candidates,
)


def test_equity_need_zero_inbound():
    """Test that zero inbound links gives max equity need."""
    assert equity_need(0) == 1.0


def test_equity_need_high_inbound():
    """Test that high inbound links gives low equity need."""
    assert equity_need(100) < 0.02


def test_final_score_pure_similarity():
    """Test that alpha=1.0 means pure similarity."""
    score = final_score(similarity=0.88, inbound_links=0, alpha=1.0)
    assert score == pytest.approx(0.88)


def test_final_score_prefers_orphan():
    """Test that orphan with lower similarity outscores popular with higher."""
    orphan_score = final_score(similarity=0.85, inbound_links=0, alpha=0.7)
    popular_score = final_score(similarity=0.91, inbound_links=48, alpha=0.7)
    assert orphan_score > popular_score


def test_rerank_candidates_sorts_by_final_score():
    """Test that reranked results are sorted by final_score descending."""
    candidates = [
        {"url": "a", "score": 0.9, "text": "a"},
        {"url": "b", "score": 0.8, "text": "b"},
        {"url": "c", "score": 0.7, "text": "c"},
    ]
    reranked = rerank_candidates(candidates)
    assert reranked[0]["final_score"] >= reranked[1]["final_score"]


def test_rerank_candidates_adds_equity_fields():
    """Test that reranking adds equity_need_score and inbound_link_count."""
    from backend.core.rerank import init_link_graph

    init_link_graph({"url1": 5})

    candidates = [{"url": "url1", "score": 0.8, "text": "test"}]
    result = rerank_candidates(candidates)

    assert "equity_need_score" in result[0]
    assert "inbound_link_count" in result[0]
    assert "final_score" in result[0]


def test_collapse_candidates_by_url_keeps_best_scoring_chunk():
    """Test that duplicate chunks collapse into one URL candidate."""
    candidates = [
        {"url": "url1", "score": 0.81, "chunk_text": "lower"},
        {"url": "url1", "score": 0.92, "chunk_text": "higher"},
        {"url": "url2", "score": 0.78, "chunk_text": "other"},
    ]

    collapsed = collapse_candidates_by_url(candidates)

    assert len(collapsed) == 2
    assert collapsed[0]["chunk_text"] == "higher"
    assert collapsed[0]["score"] == 0.92


def test_rerank_candidates_filters_excluded_urls():
    """Test that reranking can exclude URLs already selected elsewhere."""
    from backend.core.rerank import init_link_graph

    init_link_graph({"url1": 0, "url2": 1})

    candidates = [
        {"url": "url1", "score": 0.8, "chunk_text": "first"},
        {"url": "url2", "score": 0.79, "chunk_text": "second"},
    ]
    result = rerank_candidates(candidates, excluded_urls={"url1"})

    assert [candidate["url"] for candidate in result] == ["url2"]

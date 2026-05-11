# ----- equity evaluation tests @ backend/tests/test_eval/test_eval_equity.py -----
from backend.eval.eval_equity import (
    apply_recommendations,
    compute_gini,
    compute_orphan_reduction,
    summarize_graph_distribution,
)


def test_apply_recommendations_updates_full_graph_distribution():
    """Test projected graph adds recommendations on top of every indexed URL."""
    original_graph = {
        "https://example.com/orphan": 0,
        "https://example.com/mid": 2,
        "https://example.com/popular": 5,
    }

    projected_graph = apply_recommendations(
        original_graph,
        [
            "https://example.com/orphan",
            "https://example.com/orphan",
            "https://example.com/mid",
        ],
    )

    assert projected_graph == {
        "https://example.com/orphan": 2,
        "https://example.com/mid": 3,
        "https://example.com/popular": 5,
    }


def test_compute_gini_uses_full_projected_distribution():
    """Test gini is computed from the full graph, including untouched URLs."""
    baseline_graph = {
        "https://example.com/orphan": 0,
        "https://example.com/mid": 2,
        "https://example.com/popular": 5,
    }
    equity_graph = apply_recommendations(
        baseline_graph,
        ["https://example.com/orphan", "https://example.com/orphan"],
    )

    baseline_gini = compute_gini(list(baseline_graph.values()))
    equity_gini = compute_gini(list(equity_graph.values()))

    assert equity_gini < baseline_gini


def test_compute_orphan_reduction_uses_original_orphan_set():
    """Test orphan rescue is measured against the original graph state."""
    link_graph = {
        "https://example.com/orphan": 0,
        "https://example.com/mid": 2,
        "https://example.com/popular": 5,
    }

    orphan_reduction = compute_orphan_reduction(
        {
            "https://example.com/orphan",
            "https://example.com/popular",
        },
        link_graph,
    )

    assert orphan_reduction == 1.0


def test_summarize_graph_distribution_reports_orphans_and_top_urls():
    """Test graph summary exposes the data needed to debug the hashmap."""
    link_graph = {
        "https://example.com/orphan": 0,
        "https://example.com/mid": 2,
        "https://example.com/popular": 5,
    }

    summary = summarize_graph_distribution(link_graph)

    assert summary["url_count"] == 3
    assert summary["orphan_count"] == 1
    assert summary["orphan_sample"] == ["https://example.com/orphan"]
    assert summary["max_inbound"] == 5
    assert summary["top_inbound_urls"][0] == ("https://example.com/popular", 5)

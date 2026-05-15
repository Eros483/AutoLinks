# ----- equity evaluation tests @ backend/tests/test_eval/test_eval_equity.py -----
from backend.eval.eval_equity import (
    apply_recommendations,
    build_synthetic_link_graph,
    compute_gini,
    compute_orphan_reduction,
    generate_synthetic_candidate_batches,
    run_synthetic_equity_evaluation,
    select_synthetic_recommendations,
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


def test_build_synthetic_link_graph_creates_expected_orphan_pool():
    """Test synthetic graph builder creates deterministic orphan coverage."""
    graph = build_synthetic_link_graph(total_urls=20, orphan_ratio=0.20, seed=7)

    orphan_count = sum(1 for inbound_count in graph.values() if inbound_count == 0)

    assert len(graph) == 20
    assert orphan_count == 4


def test_generate_synthetic_candidate_batches_only_uses_graph_urls():
    """Test synthetic candidates are drawn from the generated graph."""
    graph = build_synthetic_link_graph(total_urls=30, seed=9)

    candidate_batches = generate_synthetic_candidate_batches(
        graph,
        num_drafts=3,
        candidates_per_draft=8,
        seed=9,
    )

    assert len(candidate_batches) == 3
    assert all(len(batch) == 8 for batch in candidate_batches)
    assert all(
        candidate["url"] in graph for batch in candidate_batches for candidate in batch
    )


def test_select_synthetic_recommendations_prefers_more_orphans_with_equity():
    """Test synthetic equity-aware ranking selects more orphan URLs than baseline."""
    graph = {
        "https://synthetic.test/orphan": 0,
        "https://synthetic.test/low": 2,
        "https://synthetic.test/popular": 50,
    }
    candidate_batches = [
        [
            {"url": "https://synthetic.test/popular", "score": 0.99},
            {"url": "https://synthetic.test/orphan", "score": 0.80},
            {"url": "https://synthetic.test/low", "score": 0.82},
        ]
    ]

    baseline_urls, _ = select_synthetic_recommendations(
        candidate_batches,
        graph,
        alpha=1.0,
        recommendations_per_draft=1,
    )
    equity_urls, _ = select_synthetic_recommendations(
        candidate_batches,
        graph,
        alpha=0.7,
        recommendations_per_draft=1,
    )

    assert baseline_urls == ["https://synthetic.test/popular"]
    assert equity_urls == ["https://synthetic.test/orphan"]


def test_run_synthetic_equity_evaluation_produces_measurable_lift():
    """Test the synthetic harness shows equity improvements under default constraints."""
    results = run_synthetic_equity_evaluation(total_urls=60, seed=13)

    assert results["gini_improved"] is True
    assert results["orphan_lifted"] is True
    assert results["equity_unique_urls"] >= results["baseline_unique_urls"]

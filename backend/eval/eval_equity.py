# ----- equity distribution evaluation script @ backend/eval/eval_equity.py -----
"""
Eval 4 - Link Equity Distribution (Graph Health) Evaluation

Compares equity-aware re-ranking (α=0.7) vs pure similarity baseline (α=1.0)
across 50 draft samples. Computes Gini coefficient and orphan reduction rate.

Target: Equity-aware system achieves lower Gini coefficient and higher orphan
reduction than pure similarity baseline while maintaining >90% semantic accuracy.
"""

import argparse
import os
import random

import requests
from backend.utils.logger import logger

API_BASE = os.environ.get("EVAL_API_URL", "http://localhost:8000/api/v1")
NUM_DRAFTS = 50
EVAL_MIN_SIMILARITY = 0.0
SYNTHETIC_SEED = 42


test_drafts = [
    # --- Theme: Artificial Intelligence & Superintelligence ---
    "When we finally achieve Artificial General Intelligence, the timeline might accelerate much faster than we anticipate.",
    "The jump from human-level AI to Artificial Superintelligence could happen in a matter of hours, catching humanity off guard.",
    "Bostrom's concept of an intelligence explosion is critical when calculating our survival odds alongside advanced AI.",
    "If an AI is programmed to optimize paperclips, a superintelligent system might consume the entire galaxy's resources to do it.",
    "The timeline to AGI is heavily debated, but the median estimate among ML researchers is shrinking rapidly.",
    "Aligning an artificial superintelligence with human values is arguably the most important technical problem in history.",
    "We are currently standing on the 'tripwire' of the AI revolution, right before the exponential curve goes vertical.",
    "Narrow AI is already everywhere, but general intelligence requires a fundamental breakthrough in reasoning.",
    "The concept of the Turing Test is becoming less relevant as large language models demonstrate emergent behaviors.",
    "If biological intelligence is just a computational process, there is no physical law preventing machines from replicating it.",
    # --- Theme: The Fermi Paradox & Space ---
    "Given the vastness of the observable universe, the Fermi Paradox asks the obvious question: where is everybody?",
    "The Great Filter theory suggests there is an evolutionary step so improbable that almost no civilization survives it.",
    "If we are the first civilization to pass the Great Filter, humanity has a massive responsibility to colonize the galaxy.",
    "Building a Dyson Sphere would require dismantling entire planets to capture the energy output of a star.",
    "The Kardashev Scale categorizes advanced civilizations based on their ability to harness energy from their planet, star, or galaxy.",
    "Making humanity a multi-planetary species acts as a biological hard drive backup in case Earth experiences an extinction event.",
    "SpaceX's ultimate goal isn't just launching satellites; it's driving down the cost of payload to orbit to enable Mars colonization.",
    "The Drake Equation gives us a mathematical framework to estimate the number of active, communicative extraterrestrial civilizations.",
    "If faster-than-light travel is impossible, galactic colonization will rely on generational ships or advanced cryonics.",
    "The concept of the 'Dark Forest' suggests that advanced civilizations stay silent to avoid being destroyed by apex predators.",
    # --- Theme: Human Behavior, Brains & Procrastination ---
    "The Instant Gratification Monkey only cares about maximizing the ease and pleasure of the current moment.",
    "When a deadline approaches, the Panic Monster wakes up, forcing the procrastinator into a state of hyper-focus.",
    "The Rational Decision Maker in our brain often loses control of the steering wheel when a difficult task presents itself.",
    "Overcoming the Social Survival Mammoth means realizing that most people aren't actually paying attention to your mistakes.",
    "Human brains evolved for a tribal environment, making modern social media a toxic hyper-stimulus for our ancient hardware.",
    "The concept of the 'Dark Playground' describes the guilt-ridden leisure time you experience when you should be working.",
    "We all have a finite number of weeks in our life calendar, yet we spend so many of them entirely on autopilot.",
    "The 'Cook vs. Chef' analogy perfectly illustrates the difference between blindly following the crowd and reasoning from first principles.",
    "High-bandwidth brain-machine interfaces like Neuralink could eventually allow for non-verbal conceptual telepathy.",
    "The human neocortex is responsible for our highest-level reasoning, separating us from the purely reactive limbic system.",
    # --- Theme: Deep Time, History, and Scale ---
    "If you compress the entire history of Earth into a single calendar year, modern humans only appear in the final seconds of December 31st.",
    "The exponential growth of technological progress means the 21st century will experience far more change than the previous millennium.",
    "Understanding deep time requires breaking past our cognitive biases, which are tuned to understand days and years, not eons.",
    "The agricultural revolution fundamentally changed human social structures, moving us from egalitarian tribes to hierarchical societies.",
    "We are currently living in the Anthropocene, the first geological epoch defined entirely by the impact of a single species.",
    "The story of human progress is largely the story of our increasing ability to capture, store, and transmit information.",
    "Writing was the first great technological leap that allowed human knowledge to compound across generations.",
    "The industrial revolution replaced biological muscle power with the immense stored energy of fossil fuels.",
    "When you look at a family tree going back hundreds of generations, you realize how genetically interconnected the entire human race is.",
    "The concept of 'emergence' explains how simple rules at a micro level can create incredibly complex behaviors at a macro level.",
    # --- Theme: First Principles, Careers, and Life Choices ---
    "Picking a career path is often paralyzed by the fear of closing doors, but staying in the hallway indefinitely is the worst option.",
    "First-principles thinking requires stripping a problem down to its fundamental physical truths and building up from there.",
    "The 'Epiphany Phase' of a new relationship eventually fades, forcing couples to rely on deep compatibility rather than just neurochemistry.",
    "We often base our self-worth on the approval of a phantom audience that exists entirely within our own heads.",
    "The sunk cost fallacy keeps people trapped in unfulfilling jobs simply because they've already invested years into the path.",
    "True deep work requires disconnecting completely from the constant dopamine drip of the modern internet.",
    "The difference between a growth mindset and a fixed mindset determines how you handle inevitable failures in a new venture.",
    "Imposter syndrome is incredibly common among high achievers because they are hyper-aware of the gap between their taste and their current output.",
    "Choosing a life partner is essentially picking your permanent roommate, financial partner, and co-parent for the next fifty years.",
    "The pursuit of happiness often backfires; meaning and fulfillment are usually byproducts of solving difficult, worthwhile problems.",
]


def compute_gini(link_counts):
    """
    Compute Gini coefficient for link distribution.

    Args:
        link_counts: List of inbound link counts per URL

    Returns:
        Float between 0 (perfect equality) and 1 (maximum inequality)
    """
    if not link_counts:
        return 0.0

    sorted_counts = sorted(link_counts)
    n = len(sorted_counts)
    cumsum = 0

    for i, count in enumerate(sorted_counts):
        cumsum += (i + 1) * count

    total = sum(sorted_counts)
    if total == 0:
        return 0.0

    gini = (2 * cumsum) / (n * total) - (n + 1) / n
    return max(0.0, min(1.0, gini))


def apply_recommendations(link_graph, recommended_urls):
    """
    Project inbound link counts after applying new recommendations.

    Args:
        link_graph: Dict mapping URL to current inbound link count
        recommended_urls: Ordered list of URLs recommended across drafts

    Returns:
        New link graph with added inbound links for each recommendation
    """
    projected_graph = dict(link_graph)

    for url in recommended_urls:
        if url not in projected_graph:
            continue
        projected_graph[url] += 1

    return projected_graph


def compute_orphan_reduction(recommended_urls, link_graph):
    """
    Compute percentage of orphan pages (0 inbound links) that received at least one recommendation.

    Args:
        recommended_urls: Set of URLs that received recommendations
        link_graph: Dict mapping URL to inbound link count

    Returns:
        Float between 0 and 1 representing orphan reduction rate
    """
    orphan_urls = {
        url for url, inbound_count in link_graph.items() if inbound_count == 0
    }

    if not orphan_urls:
        return 0.0

    rescued = len(orphan_urls & recommended_urls)
    return rescued / len(orphan_urls)


def summarize_graph_distribution(link_graph):
    """Summarize the current inbound-link distribution for debugging."""
    inbound_counts = list(link_graph.values())
    orphan_urls = [
        url for url, inbound_count in link_graph.items() if inbound_count == 0
    ]
    top_inbound_urls = sorted(
        link_graph.items(), key=lambda item: item[1], reverse=True
    )[:5]

    return {
        "url_count": len(link_graph),
        "orphan_count": len(orphan_urls),
        "orphan_sample": orphan_urls[:5],
        "min_inbound": min(inbound_counts) if inbound_counts else 0,
        "max_inbound": max(inbound_counts) if inbound_counts else 0,
        "top_inbound_urls": top_inbound_urls,
    }


def build_synthetic_link_graph(
    total_urls=200,
    orphan_ratio=0.15,
    low_ratio=0.35,
    mid_ratio=0.30,
    seed=SYNTHETIC_SEED,
):
    """Build a deterministic synthetic graph with controlled link inequity."""
    rng = random.Random(seed)
    orphan_count = max(1, int(total_urls * orphan_ratio))
    low_count = max(1, int(total_urls * low_ratio))
    mid_count = max(1, int(total_urls * mid_ratio))
    high_count = max(1, total_urls - orphan_count - low_count - mid_count)

    graph = {}
    current_index = 1

    for _ in range(orphan_count):
        graph[f"https://synthetic.test/article-{current_index:03d}"] = 0
        current_index += 1

    for _ in range(low_count):
        graph[f"https://synthetic.test/article-{current_index:03d}"] = rng.randint(1, 3)
        current_index += 1

    for _ in range(mid_count):
        graph[f"https://synthetic.test/article-{current_index:03d}"] = rng.randint(
            4, 12
        )
        current_index += 1

    for _ in range(high_count):
        graph[f"https://synthetic.test/article-{current_index:03d}"] = rng.randint(
            25, 80
        )
        current_index += 1

    return graph


def score_url_for_alpha(similarity_score, inbound_links, alpha):
    """Mirror the production equity formula for synthetic evaluation."""
    equity_need = 1 / (1 + inbound_links)
    return alpha * similarity_score + (1 - alpha) * equity_need


def generate_synthetic_candidate_batches(
    link_graph,
    num_drafts=NUM_DRAFTS,
    candidates_per_draft=12,
    seed=SYNTHETIC_SEED,
):
    """Generate deterministic draft candidate pools with equity tradeoffs baked in."""
    rng = random.Random(seed)
    orphan_urls = [url for url, count in link_graph.items() if count == 0]
    low_urls = [url for url, count in link_graph.items() if 1 <= count <= 3]
    mid_urls = [url for url, count in link_graph.items() if 4 <= count <= 12]
    high_urls = [url for url, count in link_graph.items() if count >= 25]

    candidate_batches = []
    for draft_index in range(num_drafts):
        draft_candidates = []
        used_urls = set()

        candidate_plan = [
            (high_urls, (0.93, 0.99), 3),
            (mid_urls, (0.84, 0.92), 3),
            (low_urls, (0.76, 0.88), 3),
            (orphan_urls, (0.68, 0.82), 3),
        ]

        for url_pool, score_range, target_count in candidate_plan:
            if not url_pool:
                continue

            available_urls = [url for url in url_pool if url not in used_urls]
            sample_count = min(target_count, len(available_urls))
            if sample_count == 0:
                continue

            sampled_urls = rng.sample(available_urls, sample_count)
            for url in sampled_urls:
                used_urls.add(url)
                draft_candidates.append(
                    {
                        "url": url,
                        "score": round(rng.uniform(*score_range), 4),
                        "draft_index": draft_index,
                    }
                )

        remaining_urls = [url for url in link_graph if url not in used_urls]
        while len(draft_candidates) < candidates_per_draft and remaining_urls:
            url = rng.choice(remaining_urls)
            remaining_urls.remove(url)
            draft_candidates.append(
                {
                    "url": url,
                    "score": round(rng.uniform(0.70, 0.90), 4),
                    "draft_index": draft_index,
                }
            )

        candidate_batches.append(draft_candidates[:candidates_per_draft])

    return candidate_batches


def select_synthetic_recommendations(
    candidate_batches,
    link_graph,
    alpha,
    recommendations_per_draft=5,
):
    """Select top URLs per draft from synthetic candidate pools."""
    recommended_urls = []
    drafts_with_recommendations = 0

    for candidates in candidate_batches:
        ranked_candidates = sorted(
            candidates,
            key=lambda candidate: score_url_for_alpha(
                candidate["score"], link_graph[candidate["url"]], alpha
            ),
            reverse=True,
        )
        selected_urls = [
            candidate["url"]
            for candidate in ranked_candidates[:recommendations_per_draft]
        ]
        if selected_urls:
            drafts_with_recommendations += 1
        recommended_urls.extend(selected_urls)

    return recommended_urls, drafts_with_recommendations


def fetch_link_graph():
    """Fetch the active link graph from the running API server."""
    response = requests.get(f"{API_BASE}/link-graph", timeout=30)
    response.raise_for_status()
    payload = response.json()
    return payload.get("link_graph", {})


def emit_equity_report(
    link_graph,
    baseline_recommendations,
    equity_aware_recommendations,
    baseline_drafts_with_recommendations,
    equity_drafts_with_recommendations,
    mode_label,
):
    """Compute metrics and print a shared equity evaluation report."""
    graph_summary = summarize_graph_distribution(link_graph)
    logger.info("%s link graph summary: %s", mode_label, graph_summary)

    baseline_projected_graph = apply_recommendations(
        link_graph, baseline_recommendations
    )
    equity_projected_graph = apply_recommendations(
        link_graph, equity_aware_recommendations
    )

    baseline_gini = compute_gini(list(baseline_projected_graph.values()))
    equity_gini = compute_gini(list(equity_projected_graph.values()))

    baseline_orphan_reduction = compute_orphan_reduction(
        set(baseline_recommendations), link_graph
    )
    equity_orphan_reduction = compute_orphan_reduction(
        set(equity_aware_recommendations), link_graph
    )
    orphan_urls = {
        url for url, inbound_count in link_graph.items() if inbound_count == 0
    }
    baseline_rescued_orphans = sorted(orphan_urls & set(baseline_recommendations))
    equity_rescued_orphans = sorted(orphan_urls & set(equity_aware_recommendations))

    baseline_unique_urls = len(set(baseline_recommendations))
    equity_unique_urls = len(set(equity_aware_recommendations))

    print("\n" + "=" * 60)
    print(f"EQUITY DISTRIBUTION EVALUATION RESULTS ({mode_label})")
    print("=" * 60)
    print(f"Total Drafts:        {NUM_DRAFTS}")
    print("-" * 60)
    print("BASELINE (α = 1.0, pure similarity)")
    print(
        f"  Draft Coverage:        {baseline_drafts_with_recommendations}/{NUM_DRAFTS}"
    )
    print(f"  Total Recommendations: {len(baseline_recommendations)}")
    print(f"  Unique URLs:           {baseline_unique_urls}")
    print(f"  Gini Coefficient:      {baseline_gini:.4f}")
    print(f"  Orphan Reduction:      {baseline_orphan_reduction:.2%}")
    print("-" * 60)
    print("EQUITY-AWARE (α = 0.7)")
    print(f"  Draft Coverage:        {equity_drafts_with_recommendations}/{NUM_DRAFTS}")
    print(f"  Total Recommendations: {len(equity_aware_recommendations)}")
    print(f"  Unique URLs:           {equity_unique_urls}")
    print(f"  Gini Coefficient:      {equity_gini:.4f}")
    print(f"  Orphan Reduction:      {equity_orphan_reduction:.2%}")
    print("-" * 60)
    print("COMPARISON")
    print(
        f"  Gini Improvement:     {baseline_gini - equity_gini:.4f} ({'better' if equity_gini < baseline_gini else 'worse'})"
    )
    print(
        f"  Orphan Lift:          {(equity_orphan_reduction - baseline_orphan_reduction):.2%}"
    )
    print(
        f"  URL Distribution:     {equity_unique_urls - baseline_unique_urls:+d} unique URLs"
    )
    print("=" * 60)

    gini_improved = equity_gini < baseline_gini
    orphan_lifted = equity_orphan_reduction > baseline_orphan_reduction

    if gini_improved and orphan_lifted:
        print("RESULT: Equity-aware re-ranking SUCCESSFUL")
    else:
        print("RESULT: Equity-aware re-ranking needs tuning")

    logger.info(
        "%s eval complete: gini_improved=%s, orphan_lifted=%s",
        mode_label,
        gini_improved,
        orphan_lifted,
    )
    logger.info(
        "%s orphan diagnostics: total_orphans=%s, baseline_rescued=%s, equity_rescued=%s",
        mode_label,
        len(orphan_urls),
        len(baseline_rescued_orphans),
        len(equity_rescued_orphans),
    )
    if baseline_rescued_orphans:
        logger.info(
            "%s baseline rescued orphan sample: %s",
            mode_label,
            baseline_rescued_orphans[:5],
        )
    if equity_rescued_orphans:
        logger.info(
            "%s equity rescued orphan sample: %s",
            mode_label,
            equity_rescued_orphans[:5],
        )
    if not orphan_lifted:
        logger.warning(
            "%s: no orphan lift detected. Inspect graph composition and candidate pool constraints.",
            mode_label,
        )

    return {
        "baseline_gini": baseline_gini,
        "equity_gini": equity_gini,
        "baseline_orphan_reduction": baseline_orphan_reduction,
        "equity_orphan_reduction": equity_orphan_reduction,
        "baseline_unique_urls": baseline_unique_urls,
        "equity_unique_urls": equity_unique_urls,
        "gini_improved": gini_improved,
        "orphan_lifted": orphan_lifted,
        "graph_summary": graph_summary,
    }


def run_equity_evaluation():
    logger.info(f"Starting equity distribution evaluation with {NUM_DRAFTS} drafts")
    logger.info(f"API Base URL: {API_BASE}")

    response = requests.get(f"{API_BASE}/health")
    if response.status_code != 200:
        logger.error("API not available. Start the server first.")
        return

    link_graph = fetch_link_graph()
    if not link_graph:
        logger.error("Link graph is empty. Ingest a sitemap before running the eval.")
        return

    baseline_recommendations = []
    equity_aware_recommendations = []
    baseline_drafts_with_recommendations = 0
    equity_drafts_with_recommendations = 0

    logger.info("Running recommendations with α=1.0 (baseline - pure similarity)")

    for i in range(NUM_DRAFTS):
        draft = test_drafts[i % len(test_drafts)]

        try:
            response = requests.post(
                f"{API_BASE}/recommend",
                json={
                    "text": draft,
                    "alpha": 1.0,
                    "min_similarity": EVAL_MIN_SIMILARITY,
                },
                timeout=30,
            )
            if response.status_code == 200:
                data = response.json()
                urls = [r["suggested_url"] for r in data.get("recommendations", [])]
                baseline_recommendations.extend(urls)
                if urls:
                    baseline_drafts_with_recommendations += 1
                logger.info(
                    f"Baseline draft {i+1}/{NUM_DRAFTS}: {len(urls)} recommendations"
                )
        except Exception as e:
            logger.error(f"Baseline draft {i+1} error: {e}")

    logger.info("Running recommendations with α=0.7 (equity-aware)")

    for i in range(NUM_DRAFTS):
        draft = test_drafts[i % len(test_drafts)]

        try:
            response = requests.post(
                f"{API_BASE}/recommend",
                json={
                    "text": draft,
                    "alpha": 0.7,
                    "min_similarity": EVAL_MIN_SIMILARITY,
                },
                timeout=30,
            )
            if response.status_code == 200:
                data = response.json()
                urls = [r["suggested_url"] for r in data.get("recommendations", [])]
                equity_aware_recommendations.extend(urls)
                if urls:
                    equity_drafts_with_recommendations += 1
                logger.info(
                    f"Equity-aware draft {i+1}/{NUM_DRAFTS}: {len(urls)} recommendations"
                )
        except Exception as e:
            logger.error(f"Equity-aware draft {i+1} error: {e}")

    if not baseline_recommendations or not equity_aware_recommendations:
        logger.error("No recommendations collected - cannot compute metrics")
        return

    return emit_equity_report(
        link_graph=link_graph,
        baseline_recommendations=baseline_recommendations,
        equity_aware_recommendations=equity_aware_recommendations,
        baseline_drafts_with_recommendations=baseline_drafts_with_recommendations,
        equity_drafts_with_recommendations=equity_drafts_with_recommendations,
        mode_label="Eval 4",
    )


def run_synthetic_equity_evaluation(total_urls=200, seed=SYNTHETIC_SEED):
    """Run Eval 4 against a synthetic graph and candidate pool."""
    logger.info(
        "Starting synthetic equity evaluation: total_urls=%s, drafts=%s, seed=%s",
        total_urls,
        NUM_DRAFTS,
        seed,
    )

    link_graph = build_synthetic_link_graph(total_urls=total_urls, seed=seed)
    candidate_batches = generate_synthetic_candidate_batches(
        link_graph,
        num_drafts=NUM_DRAFTS,
        seed=seed,
    )

    baseline_recommendations, baseline_drafts_with_recommendations = (
        select_synthetic_recommendations(
            candidate_batches,
            link_graph,
            alpha=1.0,
        )
    )
    equity_aware_recommendations, equity_drafts_with_recommendations = (
        select_synthetic_recommendations(
            candidate_batches,
            link_graph,
            alpha=0.7,
        )
    )

    return emit_equity_report(
        link_graph=link_graph,
        baseline_recommendations=baseline_recommendations,
        equity_aware_recommendations=equity_aware_recommendations,
        baseline_drafts_with_recommendations=baseline_drafts_with_recommendations,
        equity_drafts_with_recommendations=equity_drafts_with_recommendations,
        mode_label="Synthetic Eval 4",
    )


def parse_args():
    """Parse command-line flags for live vs synthetic evaluation."""
    parser = argparse.ArgumentParser(description="Run AutoLinks equity evaluation")
    parser.add_argument(
        "--mode",
        choices=["live", "synthetic"],
        default="live",
        help="Use the live API-backed graph or a deterministic synthetic graph.",
    )
    parser.add_argument(
        "--synthetic-urls",
        type=int,
        default=200,
        help="Number of synthetic URLs to generate in synthetic mode.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=SYNTHETIC_SEED,
        help="Random seed for synthetic graph and candidate generation.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.mode == "synthetic":
        run_synthetic_equity_evaluation(
            total_urls=args.synthetic_urls,
            seed=args.seed,
        )
    else:
        run_equity_evaluation()

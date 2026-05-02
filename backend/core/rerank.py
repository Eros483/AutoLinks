# ----- equity-aware re-ranking @ backend/core/rerank.py -----
from typing import List, Dict, Any
from backend.utils.config import config
from backend.utils.logger import logger

link_graph: Dict[str, int] = {}


def init_link_graph(graph: Dict[str, int]) -> None:
    """Initialize the link graph with pre-computed inbound link counts."""
    global link_graph
    link_graph = graph
    logger.info(f"Link graph initialized with {len(link_graph)} URLs")


def equity_need(inbound_links: int) -> float:
    """
    Calculate equity need score for a URL.

    Args:
        inbound_links: Number of inbound internal links

    Returns:
        Float between 0 and 1, higher = more need
    """
    return 1 / (1 + inbound_links)


def final_score(similarity: float, inbound_links: int, alpha: float = None) -> float:
    """
    Compute final combined score using similarity + equity need.

    Args:
        similarity: Cosine similarity from vector search
        inbound_links: Number of inbound internal links
        alpha: Weight for similarity (1-alpha for equity)

    Returns:
        Combined score
    """
    if alpha is None:
        alpha = config.rerank_alpha

    eq_need = equity_need(inbound_links)
    return alpha * similarity + (1 - alpha) * eq_need


def rerank_candidates(
    candidates: List[Dict[str, Any]],
    alpha: float = None,
) -> List[Dict[str, Any]]:
    """
    Re-rank Qdrant results using equity-aware scoring.

    Args:
        candidates: List of {url, chunk_text, score} from Qdrant
        alpha: Similarity weight (default from config)

    Returns:
        Re-ranked list with equity_need_score and final_score added
    """
    if alpha is None:
        alpha = config.rerank_alpha

    for index, candidate in enumerate(candidates):
        url = candidate.get("url", "")
        inbound_count = link_graph.get(url, 0)
        eq_need = equity_need(inbound_count)
        sim_score = candidate.get("score", 0.0)
        final = final_score(sim_score, inbound_count, alpha)

        candidates[index] = {
            **candidate,
            "inbound_link_count": inbound_count,
            "equity_need_score": round(eq_need, 4),
            "final_score": round(final, 4),
        }

    candidates.sort(key=lambda candidate: candidate["final_score"], reverse=True)
    logger.info(f"Re-ranked {len(candidates)} candidates")
    return candidates

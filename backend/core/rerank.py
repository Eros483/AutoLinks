# ----- equity-aware re-ranking @ backend/core/rerank.py -----
import json
import redis
from typing import Any, Dict, List, Optional, Set
from backend.utils.config import config
from backend.utils.logger import logger

link_graph: Dict[str, int] = {}
LINK_GRAPH_KEY = "autolinks:link_graph"


def init_link_graph(graph: Dict[str, int]) -> None:
    """Initialize the link graph with pre-computed inbound link counts."""
    global link_graph
    link_graph = graph
    _save_link_graph(graph)
    logger.info("Link graph initialized with %d URLs", len(link_graph))


def restore_link_graph() -> Dict[str, int]:
    """Restore the link graph from Redis on startup."""
    global link_graph
    try:
        if not config.redis_url:
            return {}
        rds = _get_redis()
        raw = rds.get(LINK_GRAPH_KEY)
        if raw:
            graph = json.loads(raw)
            link_graph = graph
            logger.info("Link graph restored from Redis: %d URLs", len(graph))
            return graph
    except Exception as e:
        logger.warning("Could not restore link graph from Redis: %s", e)
    return {}


def _save_link_graph(graph: Dict[str, int]) -> None:
    """Persist the link graph to Redis."""
    try:
        if not config.redis_url or not graph:
            return
        rds = _get_redis()
        rds.set(LINK_GRAPH_KEY, json.dumps(graph))
    except Exception as e:
        logger.warning("Could not save link graph to Redis: %s", e)


def _get_redis():
    redis_url = config.redis_url
    kwargs = {}
    if redis_url.startswith("rediss://"):
        kwargs["ssl_cert_reqs"] = None
    return redis.Redis.from_url(redis_url, **kwargs)


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


def collapse_candidates_by_url(
    candidates: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Collapse chunk-level search hits into one best candidate per URL.

    Args:
        candidates: List of raw Qdrant chunk hits

    Returns:
        List containing only the highest-scoring chunk for each URL
    """
    best_by_url: Dict[str, Dict[str, Any]] = {}

    for candidate in candidates:
        url = candidate.get("url", "")
        if not url:
            continue

        existing_candidate = best_by_url.get(url)
        if existing_candidate is None or candidate.get(
            "score", 0.0
        ) > existing_candidate.get("score", 0.0):
            best_by_url[url] = candidate

    return list(best_by_url.values())


def rerank_candidates(
    candidates: List[Dict[str, Any]],
    alpha: float = None,
    excluded_urls: Optional[Set[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Re-rank Qdrant results using equity-aware scoring.

    Args:
        candidates: List of {url, chunk_text, score} from Qdrant
        alpha: Similarity weight (default from config)
        excluded_urls: URLs already selected elsewhere in the response

    Returns:
        Re-ranked list with equity_need_score and final_score added
    """
    if alpha is None:
        alpha = config.rerank_alpha

    if excluded_urls is None:
        excluded_urls = set()

    unique_candidates = collapse_candidates_by_url(candidates)
    reranked_candidates = []

    for candidate in unique_candidates:
        url = candidate.get("url", "")
        if url in excluded_urls:
            continue

        inbound_count = link_graph.get(url, 0)
        eq_need = equity_need(inbound_count)
        sim_score = candidate.get("score", 0.0)
        final = final_score(sim_score, inbound_count, alpha)

        reranked_candidates.append(
            {
                **candidate,
                "inbound_link_count": inbound_count,
                "equity_need_score": round(eq_need, 4),
                "final_score": round(final, 4),
            }
        )

    reranked_candidates.sort(
        key=lambda candidate: candidate["final_score"], reverse=True
    )
    logger.info(
        "Re-ranked %s unique URL candidates from %s raw chunks",
        len(reranked_candidates),
        len(candidates),
    )
    return reranked_candidates

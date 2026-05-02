# ----- vector search via Qdrant @ backend/core/search.py -----
from typing import List, Dict, Any

from backend.utils.config import config
from backend.utils.qdrant import get_qdrant_client
from backend.utils.logger import logger


def search_similar(
    query_embedding: List[float],
    limit: int = 10,
    min_score: float = 0.5,
) -> List[Dict[str, Any]]:
    """
    Search Qdrant for semantically similar article chunks.

    Args:
        query_embedding: Embedding vector from embed_text()
        limit: Maximum results to return
        min_score: Minimum similarity score threshold

    Returns:
        List of dicts with url, chunk_text, score
    """
    client = get_qdrant_client()

    try:
        if hasattr(client, "query_points"):
            query_response = client.query_points(
                collection_name=config.qdrant_collection,
                query=query_embedding,
                limit=limit,
                score_threshold=min_score,
                with_payload=True,
            )
            results = query_response.points
        else:
            results = client.search(
                collection_name=config.qdrant_collection,
                query_vector=query_embedding,
                limit=limit,
                score_threshold=min_score,
            )

        search_results = []
        for result in results:
            search_results.append(
                {
                    "url": result.payload.get("url", ""),
                    "chunk_text": result.payload.get("chunk_text", ""),
                    "score": float(result.score),
                }
            )

        logger.info(f"Qdrant search returned {len(search_results)} results")
        return search_results

    except Exception as e:
        logger.error(f"Qdrant search error: {e}")
        raise


def get_article_url(chunk_text: str) -> str:
    """Extract the parent article URL from chunk metadata."""
    return ""

# ----- sentence embedding generation @ backend/core/embed.py -----
import json
from typing import List

import httpx

from backend.utils.config import config
from backend.utils.logger import logger


def embed_text(text: str) -> List[float]:
    """
    Generate embedding vector for text.

    Uses HF Space in production, local SentenceTransformer as dev fallback.
    """
    return embed_batch([text])[0]


def embed_batch(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for a batch of texts.

    Uses HF Space in production, local SentenceTransformer as dev fallback.
    """
    if config.models_space_url:
        return _embed_via_space(texts)

    return _embed_via_local(texts)


def get_embedding_model():
    """Lazy-load the local sentence transformer model (dev fallback only)."""
    return _get_local_model()


# ---------------------------------------------------------------------------
# HF Space path
# ---------------------------------------------------------------------------
def _embed_via_space(texts: List[str]) -> List[List[float]]:
    from backend.core.extract import _call_space

    texts_json = json.dumps(texts)
    result = _call_space("embed_text", texts_json)
    embeddings = json.loads(result)
    logger.info("Generated %d embeddings via HF Space", len(embeddings))
    return embeddings


# ---------------------------------------------------------------------------
# Local dev fallback
# ---------------------------------------------------------------------------
_local_model = None


def _get_local_model():
    global _local_model
    if _local_model is None:
        logger.info("Loading local embedding model: %s", config.embedding_model)
        from sentence_transformers import SentenceTransformer

        _local_model = SentenceTransformer(config.embedding_model)
        logger.info("Local embedding model loaded")
    return _local_model


def _embed_via_local(texts: List[str]) -> List[List[float]]:
    model = _get_local_model()
    embeddings = model.encode(texts, convert_to_numpy=True)
    result = [e.tolist() for e in embeddings]
    logger.info("Generated %d embeddings via local model", len(result))
    return result

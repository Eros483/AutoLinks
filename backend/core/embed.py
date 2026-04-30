# ----- sentence embedding generation @ backend/core/embed.py -----
from typing import List
import numpy as np
from sentence_transformers import SentenceTransformer
from backend.utils.config import config
from backend.utils.logger import logger

_model = None


def get_embedding_model():
    """Lazy-load the sentence transformer model."""
    global _model
    if _model is None:
        logger.info(f"Loading embedding model: {config.embedding_model}")
        _model = SentenceTransformer(config.embedding_model)
        logger.info("Embedding model loaded")
    return _model


def embed_text(text: str) -> List[float]:
    """
    Generate embedding vector for text using local MiniLM model.

    Args:
        text: Text to embed

    Returns:
        List of floats representing the embedding vector
    """
    model = get_embedding_model()
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding.tolist()


def embed_batch(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for a batch of texts.

    Args:
        texts: List of texts to embed

    Returns:
        List of embedding vectors
    """
    model = get_embedding_model()
    embeddings = model.encode(texts, convert_to_numpy=True)
    return [e.tolist() for e in embeddings]

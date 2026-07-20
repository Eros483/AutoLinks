# ----- Qdrant client utilities @ backend/utils/qdrant.py -----
from typing import Any, Dict
from urllib.parse import urlparse, urlunparse

from backend.utils.config import config
from backend.utils.logger import logger

try:
    import qdrant_client
except ModuleNotFoundError:
    qdrant_client = None

_client = None


def _normalize_qdrant_url(raw_url: str) -> str:
    """Ensure self-hosted Qdrant URLs include port 6333. Cloud URLs pass through unchanged."""
    parsed_url = urlparse(raw_url)
    if not parsed_url.scheme or not parsed_url.netloc:
        return raw_url

    if parsed_url.port or parsed_url.hostname in {"localhost", "127.0.0.1"}:
        return raw_url

    if parsed_url.scheme == "https" or ".cloud.qdrant.io" in parsed_url.hostname:
        return raw_url

    return urlunparse(
        (
            parsed_url.scheme,
            f"{parsed_url.hostname}:6333",
            parsed_url.path,
            parsed_url.params,
            parsed_url.query,
            parsed_url.fragment,
        )
    )


def create_qdrant_client():
    """Create a Qdrant client for local or hosted deployments."""
    if qdrant_client is None:
        raise ModuleNotFoundError("qdrant_client is required to create a Qdrant client")

    normalized_url = _normalize_qdrant_url(config.qdrant_url)
    client_kwargs: Dict[str, Any] = {"url": normalized_url}
    if normalized_url.startswith("http://localhost") or normalized_url.startswith(
        "http://127.0.0.1"
    ):
        client_kwargs["check_compatibility"] = False
    if config.qdrant_api_key:
        client_kwargs["api_key"] = config.qdrant_api_key

    return qdrant_client.QdrantClient(**client_kwargs)


def get_qdrant_client():
    """Lazy-init a shared Qdrant client instance."""
    global _client
    if _client is None:
        _client = create_qdrant_client()
        logger.info("Qdrant client initialized")
    return _client


def ensure_collection(vector_size: int = 384):
    """Create collection if it doesn't exist."""
    client = get_qdrant_client()
    from qdrant_client.models import Distance, VectorParams

    collections = client.get_collections().collections
    if not any(c.name == config.qdrant_collection for c in collections):
        client.create_collection(
            collection_name=config.qdrant_collection,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        logger.info(f"Created collection: {config.qdrant_collection}")

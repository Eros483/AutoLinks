# ----- Qdrant client utilities @ backend/utils/qdrant.py -----
from typing import Any, Dict

from backend.utils.config import config
from backend.utils.logger import logger

try:
    import qdrant_client
except ModuleNotFoundError:
    qdrant_client = None

_client = None


def create_qdrant_client():
    """Create a Qdrant client for local or hosted deployments."""
    if qdrant_client is None:
        raise ModuleNotFoundError("qdrant_client is required to create a Qdrant client")

    client_kwargs: Dict[str, Any] = {"url": config.qdrant_url}
    if config.qdrant_url.startswith("http://localhost") or config.qdrant_url.startswith(
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

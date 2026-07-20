# ----- dead letter queue @ backend/core/dlq.py -----
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import redis

from backend.utils.config import config
from backend.utils.logger import logger

DLQ_KEY = "dlq:ingest"


def _get_redis() -> redis.Redis:
    redis_url = config.redis_url
    kwargs = {}
    if redis_url.startswith("rediss://"):
        redis_url += "?ssl_cert_reqs=CERT_NONE"
    return redis.Redis.from_url(redis_url)


def push_to_dlq(
    job_id: str, task_name: str, args: Dict[str, Any], error: str, retry_count: int
) -> None:
    """Push a permanently failed job to the dead letter queue."""
    entry = {
        "job_id": job_id,
        "task": task_name,
        "args": args,
        "error": error,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "retry_count": retry_count,
    }

    rds = _get_redis()
    rds.rpush(DLQ_KEY, json.dumps(entry))
    logger.warning("Pushed job %s to DLQ (retries: %d)", job_id, retry_count)


def pop_dlq_entries(count: Optional[int] = None) -> List[Dict[str, Any]]:
    """Pop and return entries from the DLQ. If count is None, pop all."""
    rds = _get_redis()
    entries = []

    if count is None:
        count = rds.llen(DLQ_KEY)

    for _ in range(count):
        raw = rds.lpop(DLQ_KEY)
        if raw is None:
            break
        entries.append(json.loads(raw))

    return entries


def get_dlq_count() -> int:
    """Return the number of entries in the DLQ."""
    rds = _get_redis()
    return rds.llen(DLQ_KEY)

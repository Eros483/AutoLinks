# ----- ingestion job manager @ backend/core/jobs.py -----
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import redis

from backend.utils.config import config
from backend.utils.logger import logger

JOB_NAMESPACE = "autolinks:job"
JOB_TTL = 86400 * 7  # 7 days

_rclient = None


def _get_redis() -> redis.Redis:
    global _rclient
    if _rclient is None:
        redis_url = config.redis_url
        kwargs = {}
        if redis_url.startswith("rediss://"):
            redis_url += "?ssl_cert_reqs=CERT_NONE"
        _rclient = redis.Redis.from_url(redis_url)
    return _rclient


def create_job(task_name: str, args: Dict[str, Any]) -> str:
    """Create a new job entry and return its job_id."""
    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    job_data = {
        "job_id": job_id,
        "status": "queued",
        "task_name": task_name,
        "args": args,
        "created_at": now,
        "updated_at": now,
        "articles_done": 0,
        "articles_total": 0,
        "errors": [],
    }

    rds = _get_redis()
    key = f"{JOB_NAMESPACE}:{job_id}"
    rds.set(key, json.dumps(job_data), ex=JOB_TTL)

    logger.info("Created job %s (%s)", job_id, task_name)
    return job_id


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a job by ID."""
    rds = _get_redis()
    key = f"{JOB_NAMESPACE}:{job_id}"
    raw = rds.get(key)
    if raw is None:
        return None
    return json.loads(raw)


def update_job(job_id: str, updates: Dict[str, Any]) -> None:
    """Atomically update fields on a job."""
    rds = _get_redis()
    key = f"{JOB_NAMESPACE}:{job_id}"
    raw = rds.get(key)
    if raw is None:
        return

    job_data = json.loads(raw)
    job_data.update(updates)
    job_data["updated_at"] = datetime.now(timezone.utc).isoformat()

    rds.set(key, json.dumps(job_data), ex=JOB_TTL)


def add_job_error(job_id: str, error: str) -> None:
    """Append an error to a job's error list."""
    rds = _get_redis()
    key = f"{JOB_NAMESPACE}:{job_id}"
    raw = rds.get(key)
    if raw is None:
        return

    job_data = json.loads(raw)
    job_data.setdefault("errors", []).append(error)
    job_data["updated_at"] = datetime.now(timezone.utc).isoformat()

    rds.set(key, json.dumps(job_data), ex=JOB_TTL)

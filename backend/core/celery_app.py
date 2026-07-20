# ----- Celery app configuration @ backend/core/celery_app.py -----
from celery import Celery
from backend.utils.config import config

_celery_app = None


def get_celery():
    global _celery_app
    if _celery_app is not None:
        return _celery_app

    broker_url = config.redis_url
    if not broker_url:
        broker_url = "redis://localhost:6379/0"

    if broker_url.startswith("rediss://"):
        broker_url += "?ssl_cert_reqs=CERT_NONE"

    _celery_app = Celery(
        "autolinks",
        broker=broker_url,
        backend=broker_url,
        broker_connection_retry_on_startup=True,
        broker_transport_options={"visibility_timeout": 3600},
    )

    _celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_acks_late=True,
        worker_prefetch_multiplier=1,
        result_expires=3600,
    )

    return _celery_app


celery_app = get_celery()

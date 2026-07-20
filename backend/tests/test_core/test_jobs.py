# ----- job manager tests @ backend/tests/test_core/test_jobs.py -----
import fakeredis
import json

from backend.core.jobs import create_job, get_job, update_job, add_job_error


def test_create_and_get_job(monkeypatch):
    fake = fakeredis.FakeRedis()
    monkeypatch.setattr("backend.core.jobs._get_redis", lambda: fake)
    monkeypatch.setattr("backend.core.jobs._rclient", fake)

    job_id = create_job(
        "crawl_sitemap", {"sitemap_url": "https://example.com/sitemap.xml"}
    )

    assert job_id is not None
    assert len(job_id) == 36

    job = get_job(job_id)
    assert job is not None
    assert job["status"] == "queued"
    assert job["task_name"] == "crawl_sitemap"
    assert job["args"]["sitemap_url"] == "https://example.com/sitemap.xml"
    assert job["articles_done"] == 0
    assert job["articles_total"] == 0


def test_update_job(monkeypatch):
    fake = fakeredis.FakeRedis()
    monkeypatch.setattr("backend.core.jobs._get_redis", lambda: fake)
    monkeypatch.setattr("backend.core.jobs._rclient", fake)

    job_id = create_job("test", {})
    update_job(job_id, {"status": "processing", "articles_total": 10})

    job = get_job(job_id)
    assert job["status"] == "processing"
    assert job["articles_total"] == 10


def test_add_job_error(monkeypatch):
    fake = fakeredis.FakeRedis()
    monkeypatch.setattr("backend.core.jobs._get_redis", lambda: fake)
    monkeypatch.setattr("backend.core.jobs._rclient", fake)

    job_id = create_job("test", {})
    add_job_error(job_id, "Test error 1")
    add_job_error(job_id, "Test error 2")

    job = get_job(job_id)
    assert len(job["errors"]) == 2
    assert "Test error 1" in job["errors"]


def test_get_job_not_found(monkeypatch):
    fake = fakeredis.FakeRedis()
    monkeypatch.setattr("backend.core.jobs._get_redis", lambda: fake)
    monkeypatch.setattr("backend.core.jobs._rclient", fake)

    job = get_job("nonexistent")
    assert job is None

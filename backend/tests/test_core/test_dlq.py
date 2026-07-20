# ----- dead letter queue tests @ backend/tests/test_core/test_dlq.py -----
import fakeredis

from backend.core.dlq import push_to_dlq, pop_dlq_entries, get_dlq_count


def test_push_and_pop_dlq(monkeypatch):
    fake = fakeredis.FakeRedis()
    monkeypatch.setattr("backend.core.dlq._get_redis", lambda: fake)

    push_to_dlq(
        job_id="job-1",
        task_name="crawl_sitemap",
        args={"sitemap_url": "https://example.com/sitemap.xml"},
        error="TimeoutError",
        retry_count=3,
    )

    assert get_dlq_count() == 1

    entries = pop_dlq_entries()

    assert len(entries) == 1
    assert entries[0]["job_id"] == "job-1"
    assert entries[0]["error"] == "TimeoutError"
    assert entries[0]["retry_count"] == 3
    assert get_dlq_count() == 0


def test_push_multiple_and_pop_n(monkeypatch):
    fake = fakeredis.FakeRedis()
    monkeypatch.setattr("backend.core.dlq._get_redis", lambda: fake)

    for i in range(5):
        push_to_dlq(
            job_id=f"job-{i}",
            task_name="crawl_sitemap",
            args={},
            error=f"Error {i}",
            retry_count=3,
        )

    assert get_dlq_count() == 5

    entries = pop_dlq_entries(count=2)

    assert len(entries) == 2
    assert get_dlq_count() == 3

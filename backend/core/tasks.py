# ----- Celery tasks for async ingestion @ backend/core/tasks.py -----
import asyncio

from backend.core.celery_app import celery_app
from backend.core.jobs import update_job, add_job_error
from backend.core.dlq import push_to_dlq
from backend.utils.logger import logger


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def crawl_and_ingest_task(self, job_id: str, sitemap_url: str, max_concurrent: int = 5):
    """
    Celery task: stream crawl sitemap one page at a time.

    Fetches, embeds, and upserts each page individually to avoid OOM.
    Builds the link graph after all pages are processed.
    """
    try:
        update_job(job_id, {"status": "processing"})

        from backend.core.ingest import (
            parse_sitemap,
            stream_fetch_embed_upsert,
            build_link_graph,
        )
        from backend.core.rerank import init_link_graph

        urls = parse_sitemap(sitemap_url)
        if not urls:
            update_job(job_id, {"status": "failed"})
            add_job_error(job_id, "No URLs found in sitemap")
            return

        update_job(
            job_id,
            {
                "articles_total": len(urls),
                "articles_done": 0,
            },
        )

        outbound_map = {}
        done = 0
        for i, url in enumerate(urls):
            links = asyncio.run(stream_fetch_embed_upsert(url))
            if links is not None:
                done += 1
                outbound_map[url] = links
            update_job(job_id, {"articles_done": i + 1})

        if outbound_map:
            graph = build_link_graph(
                {u: {"outbound_links": lnks} for u, lnks in outbound_map.items()}
            )
            init_link_graph(graph)

        update_job(
            job_id,
            {
                "status": "done",
                "articles_done": done,
            },
        )
        logger.info("Job %s completed: %d articles ingested", job_id, done)

    except Exception as exc:
        logger.error(
            "Job %s failed (attempt %d): %s", job_id, self.request.retries + 1, exc
        )
        add_job_error(job_id, str(exc))

        if self.request.retries >= self.max_retries:
            update_job(job_id, {"status": "failed"})
            push_to_dlq(
                job_id=job_id,
                task_name="crawl_sitemap",
                args={"sitemap_url": sitemap_url, "max_concurrent": max_concurrent},
                error=str(exc),
                retry_count=self.max_retries,
            )
        else:
            update_job(job_id, {"status": "retrying"})
            raise self.retry(exc=exc)

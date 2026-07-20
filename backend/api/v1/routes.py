# ----- API route handlers @ backend/api/v1/routes.py -----
import asyncio
import time
from fastapi import APIRouter, HTTPException, status
from backend.core import extract, embed, search, rerank
from backend.schemas.request import (
    RecommendRequest,
    IngestRequest,
    IngestSitemapRequest,
)
from backend.schemas.response import (
    RecommendResponse,
    IngestResponse,
    HealthResponse,
    LinkGraphResponse,
    Recommendation,
    IngestSitemapAsyncResponse,
    JobStatusResponse,
    JobResultResponse,
    RetryDeadResponse,
)
from backend.utils.logger import logger
from backend.utils.config import config

router = APIRouter(prefix="/api/v1")
SEARCH_CANDIDATE_LIMIT = 100
MAX_RECOMMENDATIONS = 10
MAX_RECOMMENDATIONS_PER_ENTITY = 3


@router.post("/recommend", response_model=RecommendResponse)
async def recommend(req: RecommendRequest):
    """Analyze draft text and return internal linking recommendations."""
    start_time = time.time()

    try:
        entities = extract.post_process_entities(extract.extract_entities(req.text))
        if not entities:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No high-quality entities found in text",
            )

        recommendations = []
        selected_urls = set()
        for entity in entities[:10]:
            query = f"{entity['text']} - {req.text[:200]}"
            query_embedding = embed.embed_text(query)

            candidates = search.search_similar(
                query_embedding,
                limit=SEARCH_CANDIDATE_LIMIT,
                min_score=req.min_similarity,
            )
            reranked = rerank.rerank_candidates(
                candidates,
                alpha=req.alpha,
                excluded_urls=selected_urls,
            )

            for candidate in reranked[:MAX_RECOMMENDATIONS_PER_ENTITY]:
                recommendations.append(
                    Recommendation(
                        exact_phrase=entity["text"],
                        context_snippet=candidate["chunk_text"][:150],
                        suggested_url=candidate["url"],
                        similarity_score=candidate["score"],
                        equity_need_score=candidate["equity_need_score"],
                        final_score=candidate["final_score"],
                        inbound_link_count=candidate["inbound_link_count"],
                    )
                )
                selected_urls.add(candidate["url"])
                if len(recommendations) >= MAX_RECOMMENDATIONS:
                    break

            if len(recommendations) >= MAX_RECOMMENDATIONS:
                break

        latency_ms = int((time.time() - start_time) * 1000)
        logger.info("Recommend completed in %dms", latency_ms)

        return RecommendResponse(
            status="success",
            latency_ms=latency_ms,
            recommendations=recommendations[:MAX_RECOMMENDATIONS],
        )

    except Exception as e:
        logger.error("Recommend error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.post("/ingest", response_model=IngestResponse)
async def ingest(req: IngestRequest):
    """Ingest a single article into the vector store."""
    try:
        from backend.core.ingest import ingest_article

        ingest_article(req.url, req.content)
        return IngestResponse(status="success", chunks_ingested=1)
    except Exception as e:
        logger.error("Ingest error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.post("/ingest/sitemap", response_model=IngestSitemapAsyncResponse)
async def ingest_sitemap(req: IngestSitemapRequest):
    """Enqueue sitemap ingestion as a background job. Returns immediately."""
    try:
        from backend.core.jobs import create_job
        from backend.core.tasks import crawl_and_ingest_task
        from backend.core.ingest import parse_sitemap

        urls = parse_sitemap(req.sitemap_url)
        if not urls:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No URLs found in sitemap",
            )

        job_id = create_job(
            "crawl_sitemap",
            {
                "sitemap_url": req.sitemap_url,
                "max_concurrent": req.max_concurrent,
            },
        )

        crawl_and_ingest_task.delay(
            job_id=job_id,
            sitemap_url=req.sitemap_url,
            max_concurrent=req.max_concurrent,
        )

        logger.info(
            "Enqueued sitemap ingestion job %s (%d articles)", job_id, len(urls)
        )

        return IngestSitemapAsyncResponse(
            job_id=job_id,
            status="queued",
            estimated_articles=len(urls),
        )
    except Exception as e:
        logger.error("Sitemap ingest enqueue error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/ingest/status/{job_id}", response_model=JobStatusResponse)
async def ingest_status(job_id: str):
    """Get the status and progress of an async ingest job."""
    from backend.core.jobs import get_job

    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    total = job.get("articles_total", 0)
    done = job.get("articles_done", 0)
    progress_pct = round((done / total) * 100, 1) if total > 0 else 0.0

    return JobStatusResponse(
        status=job.get("status", "unknown"),
        progress_pct=progress_pct,
        articles_done=done,
        total=total,
        errors=job.get("errors", []),
    )


@router.get("/ingest/result/{job_id}", response_model=JobResultResponse)
async def ingest_result(job_id: str):
    """Get the final result of a completed ingest job."""
    from backend.core.jobs import get_job

    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobResultResponse(
        status=job.get("status", "unknown"),
        chunks_ingested=job.get("articles_done", 0),
        duration_seconds=0.0,
        errors=job.get("errors", []),
    )


@router.post("/ingest/retry-dead", response_model=RetryDeadResponse)
async def ingest_retry_dead():
    """Pop and re-enqueue entries from the dead letter queue."""
    from backend.core.dlq import pop_dlq_entries
    from backend.core.tasks import crawl_and_ingest_task

    entries = pop_dlq_entries()
    retried_job_ids = []

    for entry in entries:
        job_id = entry["job_id"]
        args = entry["args"]
        crawl_and_ingest_task.delay(
            job_id=job_id,
            sitemap_url=args["sitemap_url"],
            max_concurrent=args.get("max_concurrent", 5),
        )
        retried_job_ids.append(job_id)

    logger.info("Re-enqueued %d DLQ jobs", len(retried_job_ids))
    return RetryDeadResponse(
        retried_count=len(retried_job_ids),
        job_ids=retried_job_ids,
    )


@router.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    models_available = bool(config.models_space_url)

    return HealthResponse(status="ok", model_loaded=models_available)


@router.get("/link-graph", response_model=LinkGraphResponse)
async def get_link_graph():
    """Expose the active inbound-link graph for evaluation and debugging."""
    return LinkGraphResponse(
        status="success",
        url_count=len(rerank.link_graph),
        link_graph=rerank.link_graph,
    )

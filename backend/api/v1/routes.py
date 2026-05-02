# ----- API route handlers @ backend/api/v1/routes.py -----
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
    Recommendation,
)
from backend.utils.logger import logger
from backend.utils.config import config

router = APIRouter(prefix="/api/v1")


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
        for entity in entities[:10]:
            query = f"{entity['text']} - {req.text[:200]}"
            query_embedding = embed.embed_text(query)

            candidates = search.search_similar(
                query_embedding,
                limit=20,
                min_score=req.min_similarity,
            )
            reranked = rerank.rerank_candidates(candidates, alpha=req.alpha)

            for candidate in reranked[:3]:
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

        latency_ms = int((time.time() - start_time) * 1000)
        logger.info(f"Recommend completed in {latency_ms}ms")

        return RecommendResponse(
            status="success",
            latency_ms=latency_ms,
            recommendations=recommendations[:10],
        )

    except Exception as e:
        logger.error(f"Recommend error: {e}")
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
        logger.error(f"Ingest error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.post("/ingest/sitemap", response_model=IngestResponse)
async def ingest_sitemap(req: IngestSitemapRequest):
    """Crawl sitemap and ingest all articles."""
    try:
        from backend.core.ingest import (
            parse_sitemap,
            crawl_and_extract,
            build_link_graph,
            ingest_article,
        )
        from backend.core.rerank import init_link_graph

        urls = parse_sitemap(req.sitemap_url)
        if not urls:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No URLs found in sitemap",
            )

        crawled_pages = await crawl_and_extract(urls, max_concurrent=req.max_concurrent)
        init_link_graph(build_link_graph(crawled_pages))

        for url, page_data in crawled_pages.items():
            ingest_article(url, page_data["text"])

        return IngestResponse(status="success", chunks_ingested=len(crawled_pages))

    except Exception as e:
        logger.error(f"Sitemap ingest error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    try:
        embed.get_embedding_model()
        model_loaded = True
    except Exception:
        model_loaded = False

    return HealthResponse(status="ok", model_loaded=model_loaded)

# ----- sitemap crawl, chunk, and upsert @ backend/core/ingest.py -----
import asyncio
import re
from typing import List, Dict, Any, Optional
import httpx
from xml.etree import ElementTree
import trafilatura
from backend.core.embed import embed_batch
from backend.utils.config import config
from backend.utils.logger import logger
from backend.utils.qdrant import get_qdrant_client


def chunk_text(text: str, sentences_per_chunk: int = 5) -> List[str]:
    """
    Split text into overlapping chunks of ~5 sentences each.

    Args:
        text: Full article text
        sentences_per_chunk: Number of sentences per chunk

    Returns:
        List of text chunks
    """
    sentence_pattern = r"(?<=[.!?])\s+"
    sentences = re.split(sentence_pattern, text)

    chunks = []
    for i in range(0, len(sentences), sentences_per_chunk - 2):
        chunk = " ".join(sentences[i : i + sentences_per_chunk])
        if chunk.strip():
            chunks.append(chunk)

    return chunks


async def fetch_and_extract(
    url: str, semaphore: asyncio.Semaphore
) -> tuple[str, Optional[str]]:
    """Fetch URL and extract article text using trafilatura."""
    async with semaphore:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                text = trafilatura.extract(response.text)
                return url, text
        except Exception as e:
            logger.warning(f"Failed to fetch {url}: {e}")
            return url, None


async def crawl_and_extract(urls: List[str], max_concurrent: int = 5) -> Dict[str, str]:
    """Crawl URLs concurrently and extract article text."""
    semaphore = asyncio.Semaphore(max_concurrent)
    tasks = [fetch_and_extract(url, semaphore) for url in urls]
    results = await asyncio.gather(*tasks)
    return {url: text for url, text in results if text}


def parse_sitemap(url: str) -> List[str]:
    """Parse sitemap and extract all article URLs."""
    try:
        response = httpx.get(url, timeout=10.0)
        tree = ElementTree.fromstring(response.content)

        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        urls = []
        for loc in tree.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc"):
            urls.append(loc.text)

        return urls
    except Exception as e:
        logger.error(f"Sitemap parse error: {e}")
        return []


def parse_sitemap_index(url: str) -> List[str]:
    """Parse sitemap index and return sub-sitemap URLs."""
    try:
        response = httpx.get(url, timeout=10.0)
        tree = ElementTree.fromstring(response.content)

        urls = []
        for loc in tree.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc"):
            urls.append(loc.text)

        return urls
    except Exception as e:
        logger.error(f"Sitemap index parse error: {e}")
        return []


def build_link_graph(articles: Dict[str, str]) -> Dict[str, int]:
    """Build inbound link count map by parsing article HTML for internal links."""
    graph: Dict[str, int] = {url: 0 for url in articles}

    href_pattern = re.compile(r'href=["\']([^"\']+)["\']', re.IGNORECASE)

    for url, html in articles.items():
        matches = href_pattern.findall(html)
        for href in matches:
            if href in graph:
                graph[href] = graph.get(href, 0) + 1

    return graph


def ingest_article(url: str, text: str) -> None:
    """
    Chunk text, generate embeddings, and upsert to Qdrant.

    Args:
        url: Source article URL
        text: Clean article text
    """
    from qdrant_client.models import PointStruct

    chunks = chunk_text(text)
    if not chunks:
        logger.warning(f"No chunks generated for {url}")
        return

    embeddings = embed_batch(chunks)

    client = get_qdrant_client()
    points = []
    for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
        points.append(
            PointStruct(
                id=f"{url}_{i}".replace("/", "_").replace(":", "_"),
                vector=emb,
                payload={
                    "url": url,
                    "chunk_text": chunk,
                    "chunk_index": i,
                },
            )
        )

    client.upsert(
        collection_name=config.qdrant_collection,
        points=points,
    )

    logger.info(f"Ingested {len(points)} chunks for {url}")

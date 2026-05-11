# ----- sitemap crawl, chunk, and upsert @ backend/core/ingest.py -----
import asyncio
import hashlib
import re
from collections import Counter
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse, urlunparse

import httpx
import trafilatura
from bs4 import BeautifulSoup
from xml.etree import ElementTree

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


def normalize_url(url: str) -> str:
    """Normalize URLs so sitemap entries and extracted links compare consistently."""
    parsed = urlparse(url)
    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/")

    return urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))


def extract_internal_links(html: str, base_url: str) -> List[str]:
    """Extract normalized internal links from article HTML."""
    soup = BeautifulSoup(html, "html.parser")
    domain = urlparse(base_url).netloc
    source_url = normalize_url(base_url)
    internal_links = set()

    for tag in soup.find_all("a", href=True):
        href = tag["href"]
        full_url = normalize_url(urljoin(base_url, href))
        parsed_link = urlparse(full_url)
        if parsed_link.scheme not in {"http", "https"}:
            continue
        if parsed_link.netloc != domain:
            continue
        if full_url == source_url:
            continue
        internal_links.add(full_url)

    return sorted(internal_links)


async def fetch_and_extract(
    url: str, semaphore: asyncio.Semaphore
) -> tuple[str, Optional[Dict[str, Any]]]:
    """Fetch URL once, then extract both article text and outbound internal links."""
    async with semaphore:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                normalized_url = normalize_url(url)
                html = response.text
                text = trafilatura.extract(response.text)
                if not text:
                    return normalized_url, None

                return normalized_url, {
                    "text": text,
                    "html": html,
                    "outbound_links": extract_internal_links(html, normalized_url),
                }
        except Exception as e:
            logger.warning(f"Failed to fetch {url}: {e}")
            return normalize_url(url), None


async def crawl_and_extract(
    urls: List[str], max_concurrent: int = 5
) -> Dict[str, Dict[str, Any]]:
    """Crawl URLs concurrently and return extracted text plus internal links."""
    semaphore = asyncio.Semaphore(max_concurrent)
    tasks = [fetch_and_extract(url, semaphore) for url in urls]
    results = await asyncio.gather(*tasks)
    return {url: page_data for url, page_data in results if page_data}


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


def build_link_graph(crawled_pages: Dict[str, Dict[str, Any]]) -> Dict[str, int]:
    """Build inbound link counts by inverting each page's outbound internal links."""
    graph: Dict[str, int] = {normalize_url(url): 0 for url in crawled_pages}
    matched_targets = 0
    skipped_targets: Counter[str] = Counter()
    zero_outbound_pages = 0
    total_outbound_links = 0

    for source_url, page_data in crawled_pages.items():
        outbound_links = page_data.get("outbound_links", [])
        total_outbound_links += len(outbound_links)
        if not outbound_links:
            zero_outbound_pages += 1

        for target_url in outbound_links:
            normalized_target = normalize_url(target_url)
            if normalized_target not in graph:
                skipped_targets[normalized_target] += 1
                continue
            if normalized_target == normalize_url(source_url):
                continue
            graph[normalized_target] += 1
            matched_targets += 1

    orphan_urls = [url for url, inbound_count in graph.items() if inbound_count == 0]
    top_inbound_urls = sorted(graph.items(), key=lambda item: item[1], reverse=True)[:5]
    unmatched_target_samples = skipped_targets.most_common(5)

    logger.info(
        "Link graph summary: urls=%s, total_outbound_links=%s, matched_targets=%s, unmatched_targets=%s, zero_outbound_pages=%s, orphan_urls=%s",
        len(graph),
        total_outbound_links,
        matched_targets,
        sum(skipped_targets.values()),
        zero_outbound_pages,
        len(orphan_urls),
    )
    if orphan_urls:
        logger.info("Orphan URL sample: %s", orphan_urls[:5])
    if top_inbound_urls:
        logger.info("Top inbound URLs: %s", top_inbound_urls)
    if unmatched_target_samples:
        logger.warning(
            "Internal links skipped because target is outside crawled sitemap set: %s",
            unmatched_target_samples,
        )

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
        hash_input = f"{url}_{i}"
        point_id = int(hashlib.sha256(hash_input.encode()).hexdigest()[:16], 16)
        points.append(
            PointStruct(
                id=point_id,
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

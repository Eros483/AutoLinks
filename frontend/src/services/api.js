const BASE_URL = 'http://127.0.0.1:8000/api/v1'

export async function fetchRecommendations(text, alpha = 0.7, minSimilarity = 0.65) {
  const response = await fetch(`${BASE_URL}/recommend`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      text,
      alpha,
      min_similarity: minSimilarity,
    }),
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(errorData.detail || `HTTP error ${response.status}`)
  }

  const data = await response.json()
  return {
    recommendations: data.recommendations || [],
    latency: data.latency_ms || null,
  }
}

export async function fetchSitemapStatus() {
  const response = await fetch(`${BASE_URL}/link-graph`)

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(errorData.detail || `HTTP error ${response.status}`)
  }

  const data = await response.json()

  return {
    hasSitemap: (data.url_count || 0) > 0,
    urlCount: data.url_count || 0,
  }
}

export async function ingestSitemap(sitemapUrl, maxConcurrent = 5) {
  const response = await fetch(`${BASE_URL}/ingest/sitemap`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      sitemap_url: sitemapUrl,
      max_concurrent: maxConcurrent,
    }),
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(errorData.detail || `HTTP error ${response.status}`)
  }

  const data = await response.json()

  return {
    status: data.status,
    chunksIngested: data.chunks_ingested || 0,
  }
}

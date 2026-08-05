const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8000/api/v1'

export function getApiBaseUrl(env = import.meta.env) {
  const apiBaseUrl = env?.VITE_API_BASE_URL || DEFAULT_API_BASE_URL
  return apiBaseUrl.replace(/\/$/, '')
}

export function buildApiUrl(path, env = import.meta.env) {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${getApiBaseUrl(env)}${normalizedPath}`
}

function authHeaders(token) {
  if (!token) return { 'Content-Type': 'application/json' }
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  }
}

async function resolveToken(getToken) {
  return getToken ? await getToken() : null
}

async function handleApiError(response) {
  const errorData = await response.json().catch(() => ({}))
  throw new Error(errorData.detail || `HTTP error ${response.status}`)
}

export async function fetchRecommendations(text, alpha = 0.7, minSimilarity = 0.65, getToken) {
  const token = await resolveToken(getToken)
  const response = await fetch(buildApiUrl('/recommend'), {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify({
      text,
      alpha,
      min_similarity: minSimilarity,
    }),
  })

  if (!response.ok) await handleApiError(response)

  const data = await response.json()
  return {
    recommendations: data.recommendations || [],
    latency: data.latency_ms || null,
  }
}

export async function fetchSitemapStatus(getToken) {
  const token = await resolveToken(getToken)
  const response = await fetch(buildApiUrl('/link-graph'), {
    headers: authHeaders(token),
  })

  if (!response.ok) await handleApiError(response)

  const data = await response.json()

  return {
    hasSitemap: (data.url_count || 0) > 0,
    urlCount: data.url_count || 0,
  }
}

export async function ingestSitemap(sitemapUrl, maxConcurrent = 5, getToken) {
  const token = await resolveToken(getToken)
  const response = await fetch(buildApiUrl('/ingest/sitemap'), {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify({
      sitemap_url: sitemapUrl,
      max_concurrent: maxConcurrent,
    }),
  })

  if (!response.ok) await handleApiError(response)

  const data = await response.json()

  return {
    status: data.status,
    chunksIngested: data.chunks_ingested || 0,
  }
}

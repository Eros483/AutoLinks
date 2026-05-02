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
import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  buildApiUrl,
  fetchSitemapStatus,
  ingestSitemap,
} from './api'

describe('sitemap api helpers', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('builds api urls from the configured frontend env', () => {
    expect(buildApiUrl('/health', { VITE_API_BASE_URL: 'http://localhost:9000/api/v1/' })).toBe(
      'http://localhost:9000/api/v1/health',
    )
  })

  it('maps link graph data into sitemap status', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ status: 'success', url_count: 12 }),
      }),
    )

    const result = await fetchSitemapStatus()

    expect(fetch).toHaveBeenCalledWith('http://127.0.0.1:8000/api/v1/link-graph')
    expect(result).toEqual({
      hasSitemap: true,
      urlCount: 12,
    })
  })

  it('posts the sitemap url for ingestion', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ status: 'success', chunks_ingested: 27 }),
      }),
    )

    const result = await ingestSitemap('https://example.com/post-sitemap.xml', 7)

    expect(fetch).toHaveBeenCalledWith('http://127.0.0.1:8000/api/v1/ingest/sitemap', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        sitemap_url: 'https://example.com/post-sitemap.xml',
        max_concurrent: 7,
      }),
    })
    expect(result).toEqual({
      status: 'success',
      chunksIngested: 27,
    })
  })
})

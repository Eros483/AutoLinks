import { describe, expect, it } from 'vitest'
import { buildHighlightedHtml, encodePhraseKey } from './editor_highlight'

describe('buildHighlightedHtml', () => {
  it('wraps recommended phrases in marks with stable keys', () => {
    const html = buildHighlightedHtml('Wait But Hi with Tim Urban', [
      { exact_phrase: 'Tim Urban' },
    ])

    expect(html).toContain('data-phrase-key="Tim%20Urban"')
    expect(html).toContain('<mark class="hl"')
    expect(html).toContain('Tim Urban</mark>')
  })

  it('escapes html before inserting highlights', () => {
    const html = buildHighlightedHtml('<script>alert(1)</script>', [])

    expect(html).toBe('&lt;script&gt;alert(1)&lt;/script&gt;')
  })
})

describe('encodePhraseKey', () => {
  it('encodes punctuation safely for attribute lookup', () => {
    expect(encodePhraseKey('CUDA & GPUs')).toBe('CUDA%20%26%20GPUs')
  })
})

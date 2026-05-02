export function buildHighlightedHtml(draftText, recommendations) {
  if (!recommendations.length) {
    return escapeHtml(draftText)
  }

  const uniquePhrases = [...new Set(recommendations.map((item) => item.exact_phrase))]
  let result = escapeHtml(draftText)

  uniquePhrases.forEach((phrase) => {
    const phraseKey = encodePhraseKey(phrase)
    const regex = new RegExp(`(${escapeRegex(phrase)})`, 'gi')
    result = result.replace(
      regex,
      `<mark class="hl" data-phrase-key="${phraseKey}">$1</mark>`,
    )
  })

  return result
}

export function encodePhraseKey(phrase) {
  return encodeURIComponent(phrase)
}

function escapeHtml(text) {
  const map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;',
  }

  return text.replace(/[&<>"']/g, (match) => map[match])
}

function escapeRegex(text) {
  return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

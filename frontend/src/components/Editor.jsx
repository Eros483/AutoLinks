import { useState, useRef, useEffect } from 'react'
import { useStore } from '../store/store'
import { fetchRecommendations } from '../services/api'

function Editor() {
  const [showHighlight, setShowHighlight] = useState(false)
  const textareaRef = useRef(null)
  const {
    draftText,
    setDraftText,
    recommendations,
    loading,
    setLoading,
    setRecommendations,
    setError,
    activeCardId,
  } = useStore()

  const handleAnalyze = async () => {
    if (!draftText.trim()) return
    setLoading(true)
    setError(null)
    try {
      const result = await fetchRecommendations(draftText)
      setRecommendations(result.recommendations, result.latency)
      setShowHighlight(true)
    } catch (err) {
      setError(err.message)
      setLoading(false)
    }
  }

  const handleTextChange = (e) => {
    setDraftText(e.target.value)
    setShowHighlight(false)
  }

  const getHighlightedText = () => {
    if (!recommendations.length) return escapeHtml(draftText)

    const phrases = recommendations.map(r => r.exact_phrase)
    let result = escapeHtml(draftText)

    const uniquePhrases = [...new Set(phrases)]
    uniquePhrases.forEach((phrase) => {
      const regex = new RegExp(`(${escapeRegex(phrase)})`, 'gi')
      result = result.replace(regex, `<mark class="hl" data-phrase="${phrase}">$1</mark>`)
    })

    return result
  }

  return (
    <div className="al-ep">
      <div className="al-section-label">Draft Editor</div>
      <div className="al-editor-wrapper">
        {showHighlight && recommendations.length > 0 ? (
          <div
            className="al-editor-highlight"
            dangerouslySetInnerHTML={{ __html: getHighlightedText() }}
          />
        ) : (
          <textarea
            ref={textareaRef}
            className="al-editor"
            value={draftText}
            onChange={handleTextChange}
            placeholder="Paste your draft text here to analyze for internal linking opportunities..."
          />
        )}
      </div>
      <button
        className="al-analyze"
        onClick={handleAnalyze}
        disabled={loading || !draftText.trim()}
      >
        {loading ? (
          <>
            <span className="al-spinner" />
            Analyzing...
          </>
        ) : (
          'Analyze'
        )}
      </button>
    </div>
  )
}

function escapeHtml(text) {
  const map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  }
  return text.replace(/[&<>"']/g, m => map[m])
}

function escapeRegex(string) {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

export default Editor
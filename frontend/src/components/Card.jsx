import { useStore } from '../store/store'

function Card({ recommendation, index }) {
  const { activeCardId, setActiveCard, recommendations } = useStore()

  const handleClick = () => {
    if (activeCardId === index) {
      setActiveCard(null)
    } else {
      setActiveCard(index)
      pulseHighlight(recommendation.exact_phrase)
    }
  }

  const isActive = activeCardId === index

  return (
    <div className={`al-card ${isActive ? 'on' : ''}`} onClick={handleClick}>
      <div className="al-card-phrase">{recommendation.exact_phrase}</div>
      <div className="al-card-context">{recommendation.context_snippet}</div>
      <a
        href={recommendation.suggested_url}
        className="al-card-url"
        target="_blank"
        rel="noopener noreferrer"
        onClick={(e) => e.stopPropagation()}
      >
        {truncateUrl(recommendation.suggested_url)}
      </a>
      <div className="al-card-scores">
        <span className="al-card-score">
          <span className="label">Match:</span>
          <span className="value">{recommendation.similarity_score.toFixed(2)}</span>
        </span>
        <span className="al-card-score equity">
          <span className="label">Equity:</span>
          <span className="value">{recommendation.equity_need_score.toFixed(2)}</span>
        </span>
      </div>
    </div>
  )
}

function truncateUrl(url) {
  try {
    const parsed = new URL(url)
    const path = parsed.pathname + parsed.hash
    if (path.length > 40) {
      return '...' + path.slice(-37)
    }
    return url
  } catch {
    return url.slice(0, 40) + (url.length > 40 ? '...' : '')
  }
}

function pulseHighlight(phrase) {
  setTimeout(() => {
    const marks = document.querySelectorAll(`mark.hl[data-phrase="${phrase}"]`)
    marks.forEach(mark => {
      mark.classList.add('pulse')
      setTimeout(() => {
        mark.classList.remove('pulse')
      }, 1400)
    })
  }, 50)
}

export default Card
import { useStore } from '../store/store'
import Card from './Card'

function Recommendations() {
  const { recommendations, loading, latency, error } = useStore()

  return (
    <div className="al-rp">
      <div className="al-rp-header">
        <div className="al-section-label">Recommendations</div>
        {latency && (
          <span className="al-latency">{latency}ms</span>
        )}
      </div>

      {error && (
        <div className="al-rp-error">{error}</div>
      )}

      {loading ? (
        <div className="al-rp-loading">
          <span className="al-spinner" />
          Analyzing draft...
        </div>
      ) : !error && recommendations.length === 0 ? (
        <div className="al-rp-empty">
          Enter text in the editor and click Analyze to get link recommendations
        </div>
      ) : (
        !error && (
          <div className="al-rp-list">
            {recommendations.map((rec, index) => (
              <Card key={index} recommendation={rec} index={index} />
            ))}
          </div>
        )
      )}
    </div>
  )
}

export default Recommendations
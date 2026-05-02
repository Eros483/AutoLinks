import { useStore } from '../store/store'
import Card from './Card'

function Recommendations() {
  const { recommendations, loading, latency } = useStore()

  return (
    <div className="al-rp">
      <div className="al-rp-header">
        <div className="al-section-label">Recommendations</div>
        {latency && (
          <span className="al-latency">{latency}ms</span>
        )}
      </div>

      {loading ? (
        <div className="al-rp-loading">
          <span className="al-spinner" />
          Analyzing draft...
        </div>
      ) : recommendations.length === 0 ? (
        <div className="al-rp-empty">
          Enter text in the editor and click Analyze to get link recommendations
        </div>
      ) : (
        <div className="al-rp-list">
          {recommendations.map((rec, index) => (
            <Card key={index} recommendation={rec} index={index} />
          ))}
        </div>
      )}
    </div>
  )
}

export default Recommendations
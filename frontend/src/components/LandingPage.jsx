const featureItems = [
  {
    title: 'Named entity extraction',
    description:
      'Uses NER to detect the phrases in a draft that deserve internal links.',
  },
  {
    title: 'Semantic search',
    description:
      'Embeds each phrase and looks for meaning-level matches in your indexed article library.',
  },
  {
    title: 'Equity-aware reranking',
    description:
      'Balances similarity with inbound-link scarcity so strong content that needs internal support rises faster.',
  },
]

const workflowItems = [
  'Paste a draft into the editor and submit it for analysis.',
  'AutoLinks extracts entities and embeds them with a local MiniLM model.',
  'Qdrant retrieves the closest chunks from your ingested article set.',
  'Recommendations are reranked with link-equity need before returning to the UI.',
]

function LandingPage({ onNavigate }) {
  return (
    <div className="al-page al-home">
      <section className="al-hero">
        <div className="al-home-brand">
          <h1 className="al-home-title">AutoLinks</h1>
        </div>
        <div className="al-hero-copy">
          <h2 className="al-hero-title">Internal linking that understands meaning, not just keywords.</h2>
          <p className="al-hero-text">
            AutoLinks analyzes draft text, extracts named entities, finds semantically related articles,
            and recommends high-confidence internal links with equity-aware reranking.
          </p>
          <div className="al-hero-actions">
            <button className="al-cta al-primary-cta" onClick={() => onNavigate('workspace')}>
              Open Workspace
            </button>
          </div>
        </div>
      </section>

      <section className="al-section-block">
        <div className="al-section-heading">
          <div className="al-section-label">Core Features</div>
          <h2 className="al-subtitle">Why the recommendations feel smarter</h2>
        </div>
        <div className="al-feature-grid">
          {featureItems.map((item) => (
            <article key={item.title} className="al-surface-card">
              <h3>{item.title}</h3>
              <p>{item.description}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="al-section-block al-flow-block">
        <div className="al-section-heading">
          <div className="al-section-label">Workflow</div>
          <h2 className="al-subtitle">What happens from draft to recommendation</h2>
        </div>
        <div className="al-flow-list">
          {workflowItems.map((item, index) => (
            <div key={item} className="al-flow-item">
              <span className="al-flow-step">0{index + 1}</span>
              <p>{item}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}

export default LandingPage

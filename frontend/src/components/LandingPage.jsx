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

function LandingPage({ onNavigate }) {
  return (
    <div className="al-page al-home">
      <section className="al-hero">
        <h1 className="al-home-title">AutoLinks</h1>
        <h2 className="al-hero-subtitle">Internal linking that understands meaning, not just keywords.</h2>
        <p className="al-hero-description">
          AutoLinks analyzes draft text, extracts named entities, finds semantically related articles,
          and recommends high-confidence internal links with equity-aware reranking.
        </p>
        <div className="al-hero-actions">
          <button className="al-cta al-primary-cta" onClick={() => onNavigate('workspace')}>
            Open Workspace
          </button>
        </div>
      </section>

      <section className="al-section-block al-core-section">
        <div className="al-section-heading al-section-heading--centered">
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
    </div>
  )
}

export default LandingPage

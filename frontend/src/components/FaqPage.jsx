const faqItems = [
  {
    term: 'Internal link',
    meaning: 'A hyperlink from one page on your site to another page on the same site.',
  },
  {
    term: 'Named entity',
    meaning: 'A meaningful phrase such as a person, product, topic, or place that can anchor a useful link.',
  },
  {
    term: 'Semantic search',
    meaning: 'A search method that matches by meaning and context instead of exact keyword overlap alone.',
  },
  {
    term: 'Embedding',
    meaning: 'A numeric vector representation of text that helps the system compare meaning between phrases and articles.',
  },
  {
    term: 'Qdrant',
    meaning: 'The vector database that stores embedded article chunks and returns the closest semantic matches.',
  },
  {
    term: 'GLiNER',
    meaning: 'The entity extraction model AutoLinks uses via pioneer.ai to identify candidate phrases in a draft.',
  },
  {
    term: 'Link equity',
    meaning: 'The relative value a page receives through internal links pointing to it from other pages on the site.',
  },
  {
    term: 'Orphan page',
    meaning: 'A page with zero inbound internal links, which usually means it is hard for users and crawlers to discover.',
  },
  {
    term: 'Equity-aware reranking',
    meaning: 'A scoring step that blends similarity with a page’s need for internal links so neglected pages can be surfaced.',
  },
  {
    term: 'DRY_RUN',
    meaning: 'A development mode that skips the live GLiNER call and returns fixture data to save API credits.',
  },
]

function FaqPage() {
  return (
    <div className="al-page al-faq">
      <section className="al-section-block">
        <div className="al-section-heading">
          <div className="al-section-label">FAQs</div>
          <h1 className="al-subtitle">Quick meanings for the terms you’ll see in AutoLinks</h1>
          <p className="al-section-copy">
            This is part glossary, part FAQ. It is meant to make the recommendation workflow easier to read at a glance.
          </p>
        </div>
        <div className="al-faq-grid">
          {faqItems.map((item) => (
            <article key={item.term} className="al-surface-card al-faq-card">
              <h3>{item.term}</h3>
              <p>{item.meaning}</p>
            </article>
          ))}
        </div>
      </section>
    </div>
  )
}

export default FaqPage

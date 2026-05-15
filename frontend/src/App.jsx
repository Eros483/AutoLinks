import { useState } from 'react'
import Header from './components/Header'
import LandingPage from './components/LandingPage'
import Layout from './components/Layout'
import FaqPage from './components/FaqPage'
import SitemapPage from './components/SitemapPage'

function App() {
  const [currentView, setCurrentView] = useState('home')

  const renderCurrentView = () => {
    if (currentView === 'workspace') {
      return <Layout />
    }

    if (currentView === 'faq') {
      return <FaqPage />
    }

    if (currentView === 'sitemap') {
      return <SitemapPage />
    }

    return <LandingPage onNavigate={setCurrentView} />
  }

  return (
    <div id="al">
      <div className="al-app">
        <Header currentView={currentView} onNavigate={setCurrentView} />
        {renderCurrentView()}
      </div>
    </div>
  )
}

export default App

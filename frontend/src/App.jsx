import { useState } from 'react'
import { Analytics } from '@vercel/analytics/react'
import Header from './components/Header'
import LandingPage from './components/LandingPage'
import Layout from './components/Layout'
import SitemapPage from './components/SitemapPage'

function App() {
  const [currentView, setCurrentView] = useState('home')

  const renderCurrentView = () => {
    if (currentView === 'workspace') {
      return <Layout />
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
      <Analytics />
    </div>
  )
}

export default App

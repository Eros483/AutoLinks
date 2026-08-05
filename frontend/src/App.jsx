import { useState } from 'react'
import { SignedIn, SignedOut, SignIn } from '@clerk/clerk-react'
import { Analytics } from '@vercel/analytics/react'
import Header from './components/Header'
import LandingPage from './components/LandingPage'
import Layout from './components/Layout'
import SitemapPage from './components/SitemapPage'

function App() {
  const [currentView, setCurrentView] = useState('home')

  return (
    <div id="al">
      <div className="al-app">
        <Header currentView={currentView} onNavigate={setCurrentView} />
        {currentView === 'home' ? (
          <LandingPage onNavigate={setCurrentView} />
        ) : (
          <>
            <SignedOut>
              <SignIn routing="virtual" />
            </SignedOut>
            <SignedIn>
              {currentView === 'workspace' && <Layout />}
              {currentView === 'sitemap' && <SitemapPage />}
            </SignedIn>
          </>
        )}
      </div>
      <Analytics />
    </div>
  )

}

export default App

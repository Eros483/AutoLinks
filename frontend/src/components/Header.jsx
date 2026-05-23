import { useState, useEffect, useRef } from 'react'
import { useStore } from '../store/store'

const navItems = [
  { id: 'home', label: 'Home' },
  { id: 'workspace', label: 'Workspace' },
  { id: 'sitemap', label: 'Sitemaps' },
]

const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8000/api/v1'

function getApiDocsUrl() {
  const apiBase = import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL
  try {
    return new URL(apiBase).origin + '/docs'
  } catch {
    return 'http://127.0.0.1:8000/docs'
  }
}

function Header({ currentView, onNavigate }) {
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const dropdownRef = useRef(null)
  const { theme, setTheme } = useStore()

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleNavigate = (view) => {
    onNavigate(view)
    setDropdownOpen(false)
  }

  return (
    <header className="al-header">
      <button className="al-logo al-logo-btn" onClick={() => onNavigate('home')}>
        AutoLinks
      </button>
      <nav className="al-nav" aria-label="Primary">
        {navItems.map((item) => (
          <button
            key={item.id}
            className={`al-nav-tab ${currentView === item.id ? 'selected' : ''}`}
            onClick={() => onNavigate(item.id)}
          >
            {item.label}
          </button>
        ))}
      </nav>
      <span className="al-tagline">Arnab</span>
      <div className="al-user" ref={dropdownRef}>
        <button
          className="al-avatar"
          onClick={() => setDropdownOpen(!dropdownOpen)}
          aria-label="User menu"
        >
          A
        </button>
        <div className={`al-dropdown ${dropdownOpen ? '' : 'hidden'}`}>
          <div className="al-dropdown-label">Theme</div>
          <div className="al-theme-options">
            <button
              className={`al-theme-btn ${theme === 'light' ? 'selected' : ''}`}
              onClick={() => setTheme('light')}
            >
              Light
            </button>
            <button
              className={`al-theme-btn ${theme === 'dark' ? 'selected' : ''}`}
              onClick={() => setTheme('dark')}
            >
              Dark
            </button>
            <button
              className={`al-theme-btn ${theme === 'system' ? 'selected' : ''}`}
              onClick={() => setTheme('system')}
            >
              System
            </button>
          </div>
          <div className="al-dropdown-label">Navigate</div>
          {navItems.map((item) => (
            <button
              key={item.id}
              className="al-dropdown-item"
              onClick={() => handleNavigate(item.id)}
            >
              {item.label}
            </button>
          ))}
          <a
            className="al-dropdown-item al-dropdown-link"
            href={getApiDocsUrl()}
            target="_blank"
            rel="noreferrer"
            onClick={() => setDropdownOpen(false)}
          >
            API Docs
          </a>
        </div>
      </div>
    </header>
  )
}

export default Header

import { useState, useEffect, useRef } from 'react'
import { useStore } from '../store/store'

function Header() {
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

  return (
    <header className="al-header">
      <a href="/" className="al-logo">AutoLinks</a>
      <span className="al-tagline">Semantic Internal Linking</span>
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
          <button className="al-dropdown-item">About</button>
        </div>
      </div>
    </header>
  )
}

export default Header
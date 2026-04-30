import React from 'react'
import EditorPage from './pages/EditorPage'
import './App.css'

function App() {
  return (
    <div className="app">
      <header className="header">
        <h1>AutoLinks</h1>
        <p>Semantic Internal Linking Assistant</p>
      </header>
      <main>
        <EditorPage />
      </main>
    </div>
  )
}

export default App
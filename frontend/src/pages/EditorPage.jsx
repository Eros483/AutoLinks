import React, { useState } from 'react'
import TextEditor from '../components/TextEditor'
import RecommendationPanel from '../components/RecommendationPanel'
import { useRecommendations } from '../hooks/useRecommendations'
import './EditorPage.css'

function EditorPage() {
  const [text, setText] = useState('')
  const { recommendations, loading, error, fetchRecommendations, latency } = useRecommendations()

  const handleAnalyze = async () => {
    if (!text.trim()) return
    await fetchRecommendations(text)
  }

  return (
    <div className="editor-page">
      <div className="editor-layout">
        <div className="editor-section">
          <TextEditor
            value={text}
            onChange={setText}
            onAnalyze={handleAnalyze}
            loading={loading}
          />
        </div>
        <div className="recommendations-section">
          <RecommendationPanel
            recommendations={recommendations}
            loading={loading}
            error={error}
            latency={latency}
          />
        </div>
      </div>
    </div>
  )
}

export default EditorPage
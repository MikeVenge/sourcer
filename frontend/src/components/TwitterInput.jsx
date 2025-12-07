import { useState } from 'react'
import { Send, MessageCircle } from 'lucide-react'

export default function TwitterInput({ onSubmit }) {
  const [handles, setHandles] = useState('')
  const [topic, setTopic] = useState('')
  const [timeframe, setTimeframe] = useState('5')
  const [processingMode, setProcessingMode] = useState('batch') // 'batch' or 'individual'

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!handles.trim() || !topic.trim()) return
    
    const handleList = handles
      .split(/[\n,\s]+/)  // Split on newlines, commas, OR whitespace
      .map(h => h.trim().replace('@', ''))
      .filter(h => h.length > 0)
    
    onSubmit(handleList, topic, parseInt(timeframe), processingMode)
  }

  return (
    <div className="input-panel">
      <div className="panel-header">
        <div className="panel-icon twitter">
          <MessageCircle color="white" size={24} />
        </div>
        <div>
          <h2>Twitter Analysis</h2>
          <p>Enter Twitter handles and a topic to analyze</p>
        </div>
      </div>

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label>Twitter Handles</label>
          <textarea
            className="form-input"
            placeholder="@elonmusk&#10;@paulg&#10;@sama&#10;&#10;Enter one handle per line or comma-separated..."
            value={handles}
            onChange={(e) => setHandles(e.target.value)}
          />
        </div>

        <div className="form-group">
          <label>Topic / Keywords</label>
          <input
            type="text"
            className="form-input"
            placeholder="e.g., AI, venture investing, technology, GPUs..."
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
          />
        </div>

        <div className="form-group">
          <label>Timeframe (days)</label>
          <div className="timeframe-input">
            <input
              type="number"
              className="form-input"
              min="1"
              max="30"
              value={timeframe}
              onChange={(e) => setTimeframe(e.target.value)}
            />
            <span className="timeframe-suffix">days</span>
          </div>
          <p className="form-hint">Look back period for tweets (default: 5 days)</p>
        </div>

        <div className="form-group">
          <label>Processing Mode</label>
          <div style={{ display: 'flex', gap: '1rem', marginTop: '0.5rem' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
              <input
                type="radio"
                name="processingMode"
                value="batch"
                checked={processingMode === 'batch'}
                onChange={(e) => setProcessingMode(e.target.value)}
              />
              <span>Batch (All handles at once - faster)</span>
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
              <input
                type="radio"
                name="processingMode"
                value="individual"
                checked={processingMode === 'individual'}
                onChange={(e) => setProcessingMode(e.target.value)}
              />
              <span>Individual (One handle at a time)</span>
            </label>
          </div>
          <p className="form-hint">
            Batch: Single API call for all handles (faster). Individual: Separate call per handle (more detailed tracking).
          </p>
        </div>

        <button type="submit" className="submit-btn">
          <Send size={18} />
          Analyze Tweets
        </button>
      </form>
    </div>
  )
}

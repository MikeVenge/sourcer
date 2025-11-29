import { useState } from 'react'
import { Send, MessageCircle } from 'lucide-react'

export default function TwitterInput({ onSubmit }) {
  const [handles, setHandles] = useState('')
  const [topic, setTopic] = useState('')
  const [timeframe, setTimeframe] = useState('5')

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!handles.trim() || !topic.trim()) return
    
    const handleList = handles
      .split(/[\n,]/)
      .map(h => h.trim().replace('@', ''))
      .filter(h => h.length > 0)
    
    onSubmit(handleList, topic, parseInt(timeframe))
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

        <button type="submit" className="submit-btn">
          <Send size={18} />
          Analyze Tweets
        </button>
      </form>
    </div>
  )
}

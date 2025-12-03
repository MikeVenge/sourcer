import { useState } from 'react'
import { Send, MessageSquare } from 'lucide-react'

export default function RedditInput({ onSubmit }) {
  const [subreddit, setSubreddit] = useState('')
  const [postCount, setPostCount] = useState('10')

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!subreddit.trim()) return
    
    // Clean subreddit name (remove r/ prefix if present)
    let cleanSubreddit = subreddit.trim()
    if (cleanSubreddit.startsWith('r/')) {
      cleanSubreddit = cleanSubreddit.slice(2)
    }
    if (cleanSubreddit.startsWith('/r/')) {
      cleanSubreddit = cleanSubreddit.slice(3)
    }
    
    onSubmit(cleanSubreddit, parseInt(postCount))
  }

  return (
    <div className="input-panel">
      <div className="panel-header">
        <div className="panel-icon reddit">
          <MessageSquare color="white" size={24} />
        </div>
        <div>
          <h2>Reddit Analysis</h2>
          <p>Enter a subreddit to analyze posts and comments</p>
        </div>
      </div>

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label>Subreddit</label>
          <input
            type="text"
            className="form-input"
            placeholder="e.g., AllinPod, wallstreetbets, stocks..."
            value={subreddit}
            onChange={(e) => setSubreddit(e.target.value)}
          />
          <p className="form-hint">Enter the subreddit name (with or without r/ prefix)</p>
        </div>

        <div className="form-group">
          <label>Number of Posts</label>
          <div className="timeframe-input">
            <input
              type="number"
              className="form-input"
              min="5"
              max="20"
              value={postCount}
              onChange={(e) => setPostCount(e.target.value)}
            />
            <span className="timeframe-suffix">posts</span>
          </div>
          <p className="form-hint">How many posts to fetch (5-20)</p>
        </div>

        <button type="submit" className="submit-btn">
          <Send size={18} />
          Analyze Subreddit
        </button>
      </form>
    </div>
  )
}


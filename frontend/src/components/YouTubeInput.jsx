import { useState } from 'react'
import { Send, Youtube } from 'lucide-react'

export default function YouTubeInput({ onSubmit }) {
  const [url, setUrl] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!url.trim()) return
    onSubmit(url.trim())
  }

  // Extract video ID for preview
  const getVideoId = (url) => {
    const patterns = [
      /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)/,
      /^([a-zA-Z0-9_-]{11})$/
    ]
    for (const pattern of patterns) {
      const match = url.match(pattern)
      if (match) return match[1]
    }
    return null
  }

  const videoId = getVideoId(url)

  return (
    <div className="input-panel">
      <div className="panel-header">
        <div className="panel-icon youtube">
          <Youtube color="white" size={24} />
        </div>
        <div>
          <h2>YouTube Transcript</h2>
          <p>Enter a YouTube URL to extract the transcript</p>
        </div>
      </div>

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label>YouTube URL</label>
          <input
            type="text"
            className="form-input"
            placeholder="https://www.youtube.com/watch?v=... or https://youtu.be/..."
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
          <p className="form-hint">Paste a YouTube video URL to get its transcript</p>
        </div>

        {videoId && (
          <div style={{
            marginBottom: '1.5rem',
            borderRadius: '12px',
            overflow: 'hidden',
            border: '1px solid var(--border-color)'
          }}>
            <img 
              src={`https://img.youtube.com/vi/${videoId}/mqdefault.jpg`}
              alt="Video thumbnail"
              style={{ width: '100%', display: 'block' }}
            />
          </div>
        )}

        <button type="submit" className="submit-btn youtube">
          <Send size={18} />
          Get Transcript
        </button>
      </form>
    </div>
  )
}


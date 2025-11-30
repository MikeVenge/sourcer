import { useState, useEffect } from 'react'
import { Send, Youtube, BookOpen } from 'lucide-react'
import NotebookLMExport from './NotebookLMExport'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function YouTubeInput({ onSubmit }) {
  const [url, setUrl] = useState('')
  const [videoTitle, setVideoTitle] = useState('')

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

  // Fetch video title for NotebookLM
  useEffect(() => {
    if (videoId) {
      const fetchVideoTitle = async () => {
        try {
          const oembedUrl = `https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v=${videoId}&format=json`
          const response = await fetch(oembedUrl)
          if (response.ok) {
            const data = await response.json()
            setVideoTitle(data.title)
          }
        } catch (e) {
          console.error('Error fetching video title:', e)
        }
      }
      fetchVideoTitle()
    } else {
      setVideoTitle('')
    }
  }, [videoId])

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

        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <button type="submit" className="submit-btn youtube" style={{ flex: 1 }}>
            <Send size={18} />
            Get Transcript
          </button>
          {videoId && (
            <NotebookLMExport 
              content="" 
              sourceName={videoTitle || `YouTube Video ${videoId}`}
              sourceType="youtube"
              contentType="youtube"
              url={url.trim()}
            />
          )}
        </div>
      </form>
    </div>
  )
}


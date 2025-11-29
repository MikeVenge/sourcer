import { useState, useEffect, useRef } from 'react'
import { Youtube, Download, Check, AlertCircle, RefreshCw, Clock, Copy } from 'lucide-react'
import { downloadMarkdown } from '../utils/exportMarkdown'
import { saveMarkdownFile } from './SavedFiles'
import { saveQueryToHistory } from './QueryHistory'

// Backend API URL
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const formatDuration = (seconds) => {
  const hrs = Math.floor(seconds / 3600)
  const mins = Math.floor((seconds % 3600) / 60)
  const secs = Math.floor(seconds % 60)
  
  if (hrs > 0) {
    return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

const formatTimestamp = (seconds) => {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

export default function YouTubeResults({ data }) {
  const [loading, setLoading] = useState(false)
  const [transcript, setTranscript] = useState(null)
  const [videoInfo, setVideoInfo] = useState(null)
  const [saved, setSaved] = useState(false)
  const [copied, setCopied] = useState(false)
  const [apiError, setApiError] = useState(null)
  const [refreshing, setRefreshing] = useState(false)
  const hasLoadedRef = useRef(false)
  const urlRef = useRef('')

  const fetchTranscript = async (isRefresh = false) => {
    setLoading(true)
    if (isRefresh) setRefreshing(true)
    setApiError(null)
    
    try {
      const response = await fetch(`${API_URL}/youtube/transcript`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url: data.url })
      })
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `API error: ${response.status}`)
      }
      
      const result = await response.json()
      setTranscript(result.transcript)
      setVideoInfo(result.video_info)
      hasLoadedRef.current = true
      urlRef.current = data.url
      
      // Save to query history (only on initial load, not refresh)
      if (!isRefresh) {
        saveQueryToHistory('youtube', {
          url: data.url,
          title: result.video_info?.title
        }, `YouTube: ${result.video_info?.title?.slice(0, 30) || 'Video'}`)
      }
      
    } catch (error) {
      console.error('YouTube transcript error:', error)
      setApiError(error.message)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    if (!hasLoadedRef.current || urlRef.current !== data.url) {
      fetchTranscript(false)
    }
  }, [data])

  const generateMarkdown = () => {
    let md = `# YouTube Transcript\n\n`
    md += `**Generated:** ${new Date().toISOString()}\n\n`
    
    if (videoInfo) {
      md += `**Title:** ${videoInfo.title}\n\n`
      md += `**Channel:** ${videoInfo.channel}\n\n`
      md += `**Duration:** ${formatDuration(videoInfo.duration)}\n\n`
      md += `**URL:** ${data.url}\n\n`
    }
    
    md += `---\n\n`
    md += `## Transcript\n\n`
    
    if (transcript && transcript.length > 0) {
      transcript.forEach(segment => {
        md += `**[${formatTimestamp(segment.start)}]** ${segment.text}\n\n`
      })
    }
    
    return md
  }

  const handleSave = () => {
    const content = generateMarkdown()
    const timestamp = new Date().toISOString().split('T')[0].replace(/-/g, '')
    const safeName = (videoInfo?.title || 'video').replace(/[^a-z0-9]/gi, '_').slice(0, 30)
    const filename = `youtube_${safeName}_${timestamp}.md`
    
    downloadMarkdown(content, filename, 'youtube', { 
      url: data.url,
      title: videoInfo?.title 
    })
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  const handleCopy = () => {
    const plainText = transcript?.map(s => s.text).join(' ') || ''
    navigator.clipboard.writeText(plainText)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (loading && !transcript) {
    return (
      <div className="loading-container">
        <div className="loading-spinner" />
        <div className="loading-text">Fetching transcript...</div>
        <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '0.5rem' }}>
          This may take a few seconds
        </div>
      </div>
    )
  }

  if (apiError && !transcript) {
    return (
      <div className="results-panel">
        <div style={{
          background: 'rgba(252, 92, 101, 0.1)',
          border: '1px solid var(--accent-red)',
          borderRadius: '12px',
          padding: '2rem',
          textAlign: 'center'
        }}>
          <AlertCircle size={48} style={{ color: 'var(--accent-red)', marginBottom: '1rem' }} />
          <h3 style={{ marginBottom: '0.5rem' }}>Error Getting Transcript</h3>
          <p style={{ color: 'var(--text-secondary)' }}>{apiError}</p>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '1rem' }}>
            Make sure the video has captions/subtitles available
          </p>
        </div>
      </div>
    )
  }

  const totalDuration = transcript?.reduce((acc, s) => Math.max(acc, s.start + (s.duration || 0)), 0) || 0
  const wordCount = transcript?.reduce((acc, s) => acc + s.text.split(' ').length, 0) || 0

  return (
    <div className="results-panel">
      {/* Header */}
      <div style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--border-color)',
        borderRadius: '16px',
        padding: '1.5rem',
        marginBottom: '1rem'
      }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flex: 1 }}>
            <div className="panel-icon youtube">
              <Youtube color="white" size={24} />
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <h3 style={{ 
                fontSize: '1.1rem', 
                fontWeight: 600, 
                marginBottom: '0.25rem',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis'
              }}>
                {videoInfo?.title || 'YouTube Video'}
              </h3>
              {videoInfo?.channel && (
                <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                  {videoInfo.channel}
                </p>
              )}
            </div>
          </div>
          
          <div style={{ display: 'flex', gap: '0.5rem', flexShrink: 0 }}>
            <button 
              className="save-btn"
              onClick={() => fetchTranscript(true)}
              disabled={refreshing}
              title="Refresh transcript"
            >
              <RefreshCw size={16} className={refreshing ? 'spinning' : ''} />
            </button>
            <button 
              className="save-btn"
              onClick={handleCopy}
              disabled={copied || !transcript}
              title="Copy transcript text"
            >
              {copied ? <Check size={16} /> : <Copy size={16} />}
            </button>
            <button 
              className={`save-btn ${saved ? 'saved' : ''}`}
              onClick={handleSave}
              disabled={saved || !transcript}
            >
              {saved ? <Check size={16} /> : <Download size={16} />}
            </button>
          </div>
        </div>

        {/* Stats */}
        <div style={{
          display: 'flex',
          gap: '1.5rem',
          marginTop: '1rem',
          paddingTop: '1rem',
          borderTop: '1px solid var(--border-color)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            <Clock size={14} />
            {formatDuration(videoInfo?.duration || totalDuration)}
          </div>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            {transcript?.length || 0} segments
          </div>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            ~{wordCount.toLocaleString()} words
          </div>
        </div>
      </div>

      {/* Transcript */}
      <div style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--border-color)',
        borderRadius: '16px',
        padding: '1.5rem'
      }}>
        <h4 style={{ marginBottom: '1rem', fontSize: '0.95rem', fontWeight: 600 }}>Transcript</h4>
        
        <div style={{
          maxHeight: '500px',
          overflowY: 'auto',
          fontSize: '0.9rem',
          lineHeight: 1.8
        }}>
          {transcript?.map((segment, index) => (
            <div 
              key={index}
              style={{
                display: 'flex',
                gap: '1rem',
                marginBottom: '0.75rem',
                paddingBottom: '0.75rem',
                borderBottom: index < transcript.length - 1 ? '1px solid var(--border-color)' : 'none'
              }}
            >
              <span style={{
                color: 'var(--accent-cyan)',
                fontSize: '0.75rem',
                fontFamily: 'JetBrains Mono, monospace',
                whiteSpace: 'nowrap',
                paddingTop: '0.2rem'
              }}>
                {formatTimestamp(segment.start)}
              </span>
              <span style={{ color: 'var(--text-secondary)' }}>
                {segment.text}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}


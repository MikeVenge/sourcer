import { useState, useEffect, useRef } from 'react'
import { MessageCircle, Heart, Repeat, Eye, MessageSquare, Download, Check, User, AlertCircle, RefreshCw } from 'lucide-react'
import { generateTwitterMarkdown, downloadMarkdown } from '../utils/exportMarkdown'
import { saveQueryToHistory } from './QueryHistory'

// Backend API URL - change this to your deployed URL in production
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const formatNumber = (num) => {
  if (!num) return '0'
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M'
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K'
  }
  return num.toLocaleString()
}

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  try {
    const date = new Date(dateStr)
    const now = new Date()
    const diffMs = now - date
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
    const diffDays = Math.floor(diffHours / 24)
    
    if (diffHours < 1) return 'Just now'
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays < 7) return `${diffDays}d ago`
    return date.toLocaleDateString()
  } catch {
    return dateStr
  }
}

export default function TwitterResults({ data }) {
  const [loading, setLoading] = useState(false)
  const [posts, setPosts] = useState([])
  const [errors, setErrors] = useState([])
  const [processingStatus, setProcessingStatus] = useState('')
  const [saved, setSaved] = useState(false)
  const [apiError, setApiError] = useState(null)
  const [refreshing, setRefreshing] = useState(false)
  const hasLoadedRef = useRef(false)
  const dataKeyRef = useRef('')

  // Generate a key to identify the data request
  const getDataKey = () => {
    return JSON.stringify({
      handles: data.handles,
      topic: data.topic,
      timeframe: data.timeframe
    })
  }

  const analyzeTwitter = async (isRefresh = false) => {
    setLoading(true)
    if (isRefresh) setRefreshing(true)
    setApiError(null)
    setProcessingStatus('Connecting to API...')
    
    try {
      const response = await fetch(`${API_URL}/twitter/analyze`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          handles: data.handles,
          topic: data.topic,
          timeframe: data.timeframe || 5,
          post_count: 10
        })
      })
      
      if (!response.ok) {
        throw new Error(`API error: ${response.status} ${response.statusText}`)
      }
      
      const result = await response.json()
      
      // Posts are already sorted by views from the backend
      setPosts(result.posts || [])
      setErrors(result.errors || [])
      hasLoadedRef.current = true
      dataKeyRef.current = getDataKey()
      
      // Save to query history (only on initial load, not refresh)
      if (!isRefresh) {
        saveQueryToHistory('twitter', {
          handles: data.handles,
          topic: data.topic,
          timeframe: data.timeframe
        }, `Twitter: ${data.handles.slice(0, 2).join(', ')}${data.handles.length > 2 ? '...' : ''}`)
      }
      
    } catch (error) {
      console.error('Twitter analysis error:', error)
      setApiError(error.message)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    // Only fetch if we haven't loaded yet OR if the data has changed
    const currentKey = getDataKey()
    if (!hasLoadedRef.current || dataKeyRef.current !== currentKey) {
      analyzeTwitter(false)
    }
  }, [data])

  const handleSave = () => {
    const { content, filename } = generateTwitterMarkdown(data, posts)
    downloadMarkdown(content, filename, 'twitter', { 
      handles: data.handles, 
      topic: data.topic,
      timeframe: data.timeframe 
    })
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner" />
        <div className="loading-text">
          {processingStatus || `Analyzing tweets for "${data.topic}"...`}
          <br />
          <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.5rem', display: 'block' }}>
            {data.handles.length} accounts • Last {data.timeframe || 5} days
          </span>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.5rem', display: 'block' }}>
            Using FinChat COT API → fxtwitter.com
          </span>
        </div>
      </div>
    )
  }

  if (apiError) {
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
          <h3 style={{ marginBottom: '0.5rem' }}>API Error</h3>
          <p style={{ color: 'var(--text-secondary)' }}>{apiError}</p>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '1rem' }}>
            Make sure the backend server is running at {API_URL}
          </p>
          <code style={{ 
            display: 'block', 
            marginTop: '1rem', 
            padding: '0.5rem', 
            background: 'var(--bg-tertiary)',
            borderRadius: '4px',
            fontSize: '0.8rem'
          }}>
            cd /Users/michaelkim/code/sourcer && python -m uvicorn app:app --reload
          </code>
        </div>
      </div>
    )
  }

  // Calculate summary stats
  const totalViews = posts.reduce((sum, p) => sum + (p.views || 0), 0)
  const totalLikes = posts.reduce((sum, p) => sum + (p.likes || 0), 0)
  const uniqueAuthors = [...new Set(posts.map(p => p.author))].length

  return (
    <div className="results-panel">
      <div className="results-header">
        <div>
          <h3>Twitter Analysis: "{data.topic}"</h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '0.25rem' }}>
            {data.handles.length} accounts • Last {data.timeframe || 5} days • {uniqueAuthors} with posts
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span className="results-count">{posts.length} posts found</span>
          <button 
            className="save-btn"
            onClick={() => analyzeTwitter(true)}
            disabled={refreshing}
            title="Refresh results"
          >
            <RefreshCw size={16} className={refreshing ? 'spinning' : ''} />
            {refreshing ? 'Refreshing...' : 'Refresh'}
          </button>
          <button 
            className={`save-btn ${saved ? 'saved' : ''}`}
            onClick={handleSave}
            disabled={saved || posts.length === 0}
          >
            {saved ? <Check size={16} /> : <Download size={16} />}
            {saved ? 'Saved!' : 'Save MD'}
          </button>
        </div>
      </div>

      {/* Summary Stats */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        gap: '1rem',
        marginBottom: '1.5rem'
      }}>
        <div className="stat-card">
          <div className="stat-label">Total Views</div>
          <div className="stat-value green">{formatNumber(totalViews)}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Total Likes</div>
          <div className="stat-value purple">{formatNumber(totalLikes)}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Posts Found</div>
          <div className="stat-value orange">{posts.length}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Active Authors</div>
          <div className="stat-value" style={{ color: 'var(--twitter-blue)' }}>{uniqueAuthors}</div>
        </div>
      </div>

      {/* Errors if any */}
      {errors.length > 0 && (
        <div style={{
          background: 'rgba(252, 92, 101, 0.1)',
          border: '1px solid var(--border-color)',
          borderRadius: '8px',
          padding: '1rem',
          marginBottom: '1.5rem',
          fontSize: '0.85rem'
        }}>
          <strong style={{ color: 'var(--accent-red)' }}>
            {errors.length} error(s) occurred:
          </strong>
          <ul style={{ marginTop: '0.5rem', color: 'var(--text-muted)' }}>
            {errors.slice(0, 5).map((err, i) => (
              <li key={i}>@{err.handle}: {err.error}</li>
            ))}
            {errors.length > 5 && <li>...and {errors.length - 5} more</li>}
          </ul>
        </div>
      )}

      {/* No posts message */}
      {posts.length === 0 && (
        <div style={{
          textAlign: 'center',
          padding: '3rem',
          color: 'var(--text-muted)'
        }}>
          <MessageCircle size={48} style={{ marginBottom: '1rem', opacity: 0.5 }} />
          <p>No relevant posts found for this topic in the specified timeframe.</p>
        </div>
      )}

      {/* Posts sorted by views */}
      {posts.map((post, index) => (
        <div 
          key={post.url || index} 
          className="twitter-post"
          style={{ animationDelay: `${index * 0.05}s` }}
        >
          <div className="post-header">
            <div className="post-avatar">
              {post.author_name ? post.author_name.charAt(0).toUpperCase() : <User size={20} />}
            </div>
            <div style={{ flex: 1 }}>
              <div className="post-author">{post.author_name || 'Unknown'}</div>
              <div className="post-handle">@{post.author} · {formatDate(post.created_at)}</div>
            </div>
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '0.5rem',
              color: 'var(--accent-cyan)',
              fontSize: '0.9rem',
              fontWeight: 600
            }}>
              <Eye size={16} />
              {formatNumber(post.views)}
            </div>
          </div>
          
          <div className="post-content">{post.text}</div>
          
          {/* Quoted tweet if present */}
          {post.quoted_tweet && (
            <div style={{
              marginTop: '1rem',
              padding: '1rem',
              background: 'var(--bg-tertiary)',
              borderRadius: '8px',
              borderLeft: '3px solid var(--border-highlight)'
            }}>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
                📎 Quoted from @{post.quoted_tweet.author?.screen_name || 'unknown'}
              </div>
              <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                {post.quoted_tweet.text?.slice(0, 200)}...
              </div>
            </div>
          )}
          
          <div style={{
            display: 'flex',
            gap: '2rem',
            marginTop: '1rem',
            paddingTop: '1rem',
            borderTop: '1px solid var(--border-color)'
          }}>
            <span style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '0.5rem',
              color: 'var(--text-muted)',
              fontSize: '0.85rem'
            }}>
              <Heart size={16} />
              {formatNumber(post.likes)}
            </span>
            <span style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '0.5rem',
              color: 'var(--text-muted)',
              fontSize: '0.85rem'
            }}>
              <Repeat size={16} />
              {formatNumber(post.retweets)}
            </span>
            <span style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '0.5rem',
              color: 'var(--text-muted)',
              fontSize: '0.85rem'
            }}>
              <MessageSquare size={16} />
              {formatNumber(post.replies)}
            </span>
            <a 
              href={post.url}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                marginLeft: 'auto',
                color: 'var(--twitter-blue)',
                fontSize: '0.85rem',
                textDecoration: 'none'
              }}
              onClick={(e) => e.stopPropagation()}
            >
              View on X →
            </a>
          </div>
        </div>
      ))}
    </div>
  )
}

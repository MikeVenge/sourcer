import { useState, useEffect, useRef } from 'react'
import { MessageSquare, ArrowUp, MessageCircle, Download, Check, User, AlertCircle, RefreshCw, ExternalLink } from 'lucide-react'
import { generateRedditMarkdown, downloadMarkdown } from '../utils/exportMarkdown'
import { saveQueryToHistory } from './QueryHistory'
import NotebookLMExport from './NotebookLMExport'

// Backend API URL
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

const formatDate = (timestamp) => {
  if (!timestamp) return ''
  try {
    const date = new Date(timestamp * 1000)
    const now = new Date()
    const diffMs = now - date
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
    const diffDays = Math.floor(diffHours / 24)
    
    if (diffHours < 1) return 'Just now'
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays < 7) return `${diffDays}d ago`
    return date.toLocaleDateString()
  } catch {
    return ''
  }
}

export default function RedditResults({ data, tabId, updateTabData }) {
  // Check if we have saved results from previous session
  const hasSavedResults = data?.results && data.results.posts && data.results.posts.length > 0
  
  const [loading, setLoading] = useState(false)
  const [posts, setPosts] = useState(hasSavedResults ? data.results.posts : [])
  const [processingStatus, setProcessingStatus] = useState('')
  const [saved, setSaved] = useState(false)
  const [apiError, setApiError] = useState(null)
  const [refreshing, setRefreshing] = useState(false)
  const [expandedPosts, setExpandedPosts] = useState({})
  const hasLoadedRef = useRef(hasSavedResults)

  const analyzeReddit = async (isRefresh = false) => {
    setLoading(true)
    if (isRefresh) setRefreshing(true)
    setApiError(null)
    setProcessingStatus('Connecting to Reddit...')
    
    try {
      const response = await fetch(`${API_URL}/reddit/analyze`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          subreddit: data.subreddit,
          post_count: data.postCount || 10
        })
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `HTTP ${response.status}`)
      }

      const result = await response.json()
      setPosts(result.posts || [])
      
      // Save results to tab data for persistence
      if (updateTabData) {
        updateTabData(tabId, {
          ...data,
          results: {
            posts: result.posts || [],
            subreddit: result.subreddit
          },
          status: 'loaded'
        })
      }
      
      // Save to query history
      saveQueryToHistory('reddit', {
        subreddit: data.subreddit,
        postCount: data.postCount
      })
      
    } catch (err) {
      console.error('Reddit analysis error:', err)
      setApiError(err.message)
    } finally {
      setLoading(false)
      setRefreshing(false)
      setProcessingStatus('')
    }
  }

  useEffect(() => {
    if (!hasLoadedRef.current && data?.subreddit) {
      hasLoadedRef.current = true
      analyzeReddit()
    }
  }, [data?.subreddit])

  const handleRefresh = () => {
    analyzeReddit(true)
  }

  const handleSaveMarkdown = () => {
    const { content, filename } = generateRedditMarkdown(data, posts)
    downloadMarkdown(content, filename, 'reddit', { 
      subreddit: data.subreddit, 
      postCount: data.postCount 
    })
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  const togglePostExpanded = (postId) => {
    setExpandedPosts(prev => ({
      ...prev,
      [postId]: !prev[postId]
    }))
  }

  // Calculate stats
  const totalScore = posts.reduce((sum, p) => sum + (p.score || 0), 0)
  const totalComments = posts.reduce((sum, p) => sum + (p.num_comments || 0), 0)
  const avgUpvoteRatio = posts.length > 0 
    ? (posts.reduce((sum, p) => sum + (p.upvote_ratio || 0), 0) / posts.length * 100).toFixed(0)
    : 0

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner" />
        <div className="loading-text">
          {processingStatus || `Fetching posts from r/${data.subreddit}...`}
          <br />
          <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.5rem', display: 'block' }}>
            {data.postCount || 10} posts with comments
          </span>
        </div>
      </div>
    )
  }

  if (apiError) {
    return (
      <div className="results-panel">
        <div className="error-message" style={{ 
          padding: '2rem', 
          textAlign: 'center', 
          color: 'var(--error-color)',
          background: 'rgba(239, 68, 68, 0.1)',
          borderRadius: '12px',
          margin: '1rem'
        }}>
          <AlertCircle size={48} style={{ marginBottom: '1rem', opacity: 0.7 }} />
          <h3 style={{ marginBottom: '0.5rem' }}>Failed to fetch Reddit data</h3>
          <p style={{ color: 'var(--text-muted)', marginBottom: '1rem' }}>{apiError}</p>
          <button 
            className="submit-btn" 
            onClick={() => analyzeReddit()}
            style={{ margin: '0 auto' }}
          >
            <RefreshCw size={16} />
            Try Again
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="results-panel">
      {/* Header */}
      <div className="results-header" style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        marginBottom: '1.5rem',
        paddingBottom: '1rem',
        borderBottom: '1px solid var(--border-color)'
      }}>
        <div>
          <h2 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', margin: 0 }}>
            <MessageSquare size={24} style={{ color: '#ff4500' }} />
            r/{data.subreddit}
          </h2>
          <p style={{ color: 'var(--text-muted)', margin: '0.25rem 0 0 0', fontSize: '0.9rem' }}>
            {posts.length} posts analyzed
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button 
            className="action-btn"
            onClick={handleRefresh}
            disabled={refreshing}
            title="Refresh data"
          >
            <RefreshCw size={16} className={refreshing ? 'spin' : ''} />
            Refresh
          </button>
          <button 
            className="action-btn"
            onClick={handleSaveMarkdown}
            disabled={saved}
          >
            {saved ? <Check size={16} /> : <Download size={16} />}
            {saved ? 'Saved!' : 'Save MD'}
          </button>
          {posts.length > 0 && (
            <NotebookLMExport 
              content={generateRedditMarkdown(data, posts).content}
              sourceName={`Reddit: r/${data.subreddit}`}
              sourceType="reddit"
            />
          )}
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
          <div className="stat-label">Total Score</div>
          <div className="stat-value" style={{ color: '#ff4500' }}>{formatNumber(totalScore)}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Total Comments</div>
          <div className="stat-value purple">{formatNumber(totalComments)}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Posts Found</div>
          <div className="stat-value orange">{posts.length}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Avg Upvote %</div>
          <div className="stat-value green">{avgUpvoteRatio}%</div>
        </div>
      </div>

      {/* Posts List */}
      <div className="posts-list" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {posts.map((post, index) => (
          <div 
            key={post.id} 
            className="post-card"
            style={{
              background: 'var(--bg-secondary)',
              borderRadius: '12px',
              padding: '1.25rem',
              border: '1px solid var(--border-color)'
            }}
          >
            {/* Post Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
              <div style={{ flex: 1 }}>
                {post.flair && (
                  <span style={{
                    background: 'var(--primary-color)',
                    color: 'white',
                    padding: '2px 8px',
                    borderRadius: '4px',
                    fontSize: '11px',
                    marginRight: '0.5rem'
                  }}>
                    {post.flair}
                  </span>
                )}
                <a 
                  href={post.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ 
                    color: 'var(--text-primary)', 
                    textDecoration: 'none',
                    fontWeight: '600',
                    fontSize: '1rem',
                    lineHeight: '1.4'
                  }}
                >
                  {post.title}
                </a>
              </div>
              <span style={{ 
                color: 'var(--text-muted)', 
                fontSize: '0.8rem',
                marginLeft: '1rem',
                whiteSpace: 'nowrap'
              }}>
                #{index + 1}
              </span>
            </div>

            {/* Post Meta */}
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '1rem', 
              marginBottom: '0.75rem',
              color: 'var(--text-muted)',
              fontSize: '0.85rem'
            }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                <User size={14} />
                u/{post.author}
              </span>
              <span>{formatDate(post.created_utc)}</span>
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', color: '#ff4500' }}>
                <ArrowUp size={14} />
                {formatNumber(post.score)}
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                <MessageCircle size={14} />
                {formatNumber(post.num_comments)}
              </span>
              <span>{(post.upvote_ratio * 100).toFixed(0)}% upvoted</span>
            </div>

            {/* Post Content */}
            {post.selftext && (
              <div style={{
                background: 'var(--bg-tertiary)',
                padding: '0.75rem',
                borderRadius: '8px',
                marginBottom: '0.75rem',
                fontSize: '0.9rem',
                color: 'var(--text-secondary)',
                maxHeight: expandedPosts[post.id] ? 'none' : '100px',
                overflow: 'hidden',
                position: 'relative'
              }}>
                {post.selftext.slice(0, expandedPosts[post.id] ? undefined : 300)}
                {post.selftext.length > 300 && !expandedPosts[post.id] && '...'}
                {post.selftext.length > 300 && (
                  <button
                    onClick={() => togglePostExpanded(post.id)}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: 'var(--primary-color)',
                      cursor: 'pointer',
                      padding: '0.25rem 0',
                      marginLeft: '0.5rem',
                      fontSize: '0.85rem'
                    }}
                  >
                    {expandedPosts[post.id] ? 'Show less' : 'Show more'}
                  </button>
                )}
              </div>
            )}

            {/* Link URL if not self post */}
            {post.link_url && !post.is_self && (
              <a 
                href={post.link_url}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  color: 'var(--primary-color)',
                  fontSize: '0.85rem',
                  marginBottom: '0.75rem'
                }}
              >
                <ExternalLink size={14} />
                {post.link_url.slice(0, 60)}...
              </a>
            )}

            {/* Comments Preview */}
            {post.comments && post.comments.length > 0 && (
              <div style={{ marginTop: '0.75rem' }}>
                <div style={{ 
                  fontSize: '0.8rem', 
                  color: 'var(--text-muted)', 
                  marginBottom: '0.5rem',
                  fontWeight: '600'
                }}>
                  Top Comments ({post.comments.length})
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  {post.comments.slice(0, 3).map((comment, idx) => (
                    <div 
                      key={idx}
                      style={{
                        background: 'var(--bg-tertiary)',
                        padding: '0.5rem 0.75rem',
                        borderRadius: '6px',
                        fontSize: '0.85rem',
                        borderLeft: '3px solid var(--border-color)'
                      }}
                    >
                      <div style={{ 
                        display: 'flex', 
                        alignItems: 'center', 
                        gap: '0.5rem', 
                        marginBottom: '0.25rem',
                        color: 'var(--text-muted)',
                        fontSize: '0.75rem'
                      }}>
                        <span>u/{comment.author}</span>
                        <span>•</span>
                        <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                          <ArrowUp size={10} />
                          {formatNumber(comment.score)}
                        </span>
                      </div>
                      <div style={{ color: 'var(--text-secondary)' }}>
                        {comment.body.slice(0, 200)}{comment.body.length > 200 ? '...' : ''}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}


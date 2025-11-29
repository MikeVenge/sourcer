import { useState, useEffect } from 'react'
import { History, Search, MessageCircle, Trash2, Clock, ChevronDown, ChevronUp, Youtube } from 'lucide-react'

const HISTORY_KEY = 'sourcer_query_history'
const MAX_HISTORY_ITEMS = 50

/**
 * Get query history from localStorage
 */
export const getQueryHistory = () => {
  try {
    const saved = localStorage.getItem(HISTORY_KEY)
    return saved ? JSON.parse(saved) : []
  } catch {
    return []
  }
}

/**
 * Save a query to history
 */
export const saveQueryToHistory = (type, query, title) => {
  const history = getQueryHistory()
  
  const newItem = {
    id: Date.now(),
    type, // 'polymarket' or 'twitter'
    query,
    title,
    timestamp: new Date().toISOString()
  }
  
  // Add to beginning, remove duplicates with same query
  const filtered = history.filter(item => {
    if (item.type !== type) return true
    if (type === 'polymarket') {
      return item.query.keyword !== query.keyword
    }
    if (type === 'twitter') {
      return JSON.stringify(item.query.handles) !== JSON.stringify(query.handles) ||
             item.query.topic !== query.topic
    }
    return true
  })
  
  const updated = [newItem, ...filtered].slice(0, MAX_HISTORY_ITEMS)
  localStorage.setItem(HISTORY_KEY, JSON.stringify(updated))
  
  return updated
}

/**
 * Clear all history
 */
export const clearQueryHistory = () => {
  localStorage.removeItem(HISTORY_KEY)
}

/**
 * Delete a single history item
 */
export const deleteHistoryItem = (id) => {
  const history = getQueryHistory()
  const updated = history.filter(item => item.id !== id)
  localStorage.setItem(HISTORY_KEY, JSON.stringify(updated))
  return updated
}

/**
 * QueryHistory component - displays and manages query history
 */
export default function QueryHistory({ onSelectQuery, onClose }) {
  const [history, setHistory] = useState([])
  const [filter, setFilter] = useState('all') // 'all', 'polymarket', 'twitter'
  const [expanded, setExpanded] = useState(true)

  useEffect(() => {
    setHistory(getQueryHistory())
  }, [])

  const handleDelete = (id, e) => {
    e.stopPropagation()
    const updated = deleteHistoryItem(id)
    setHistory(updated)
  }

  const handleClearAll = () => {
    if (confirm('Clear all query history?')) {
      clearQueryHistory()
      setHistory([])
    }
  }

  const filteredHistory = history.filter(item => {
    if (filter === 'all') return true
    return item.type === filter
  })

  const formatDate = (timestamp) => {
    const date = new Date(timestamp)
    const now = new Date()
    const diff = now - date
    
    if (diff < 60000) return 'Just now'
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`
    if (diff < 604800000) return `${Math.floor(diff / 86400000)}d ago`
    return date.toLocaleDateString()
  }

  const getQuerySummary = (item) => {
    if (item.type === 'polymarket') {
      return `Search: "${item.query.keyword}"`
    }
    if (item.type === 'twitter') {
      const handles = item.query.handles?.slice(0, 3).join(', ')
      const more = item.query.handles?.length > 3 ? ` +${item.query.handles.length - 3}` : ''
      return `@${handles}${more}`
    }
    if (item.type === 'youtube') {
      return item.query.title || item.query.url?.slice(0, 40) || 'YouTube Video'
    }
    return item.title
  }

  return (
    <div style={{
      background: 'var(--bg-card)',
      border: '1px solid var(--border-color)',
      borderRadius: '16px',
      overflow: 'hidden'
    }}>
      {/* Header */}
      <div 
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '1rem 1.25rem',
          borderBottom: expanded ? '1px solid var(--border-color)' : 'none',
          cursor: 'pointer'
        }}
        onClick={() => setExpanded(!expanded)}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <History size={18} style={{ color: 'var(--accent-cyan)' }} />
          <h3 style={{ 
            fontSize: '0.9rem', 
            fontWeight: 600,
            color: 'var(--text-primary)'
          }}>
            Query History
          </h3>
          <span style={{
            background: 'var(--bg-tertiary)',
            padding: '0.15rem 0.5rem',
            borderRadius: '10px',
            fontSize: '0.75rem',
            color: 'var(--text-muted)'
          }}>
            {history.length}
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          {history.length > 0 && expanded && (
            <button
              onClick={(e) => { e.stopPropagation(); handleClearAll(); }}
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--text-muted)',
                cursor: 'pointer',
                padding: '0.25rem',
                display: 'flex',
                alignItems: 'center'
              }}
              title="Clear all history"
            >
              <Trash2 size={14} />
            </button>
          )}
          {expanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
        </div>
      </div>

      {expanded && (
        <>
          {/* Filter Tabs */}
          <div style={{
            display: 'flex',
            gap: '0.5rem',
            padding: '0.75rem 1.25rem',
            borderBottom: '1px solid var(--border-color)'
          }}>
            {[
              { key: 'all', label: 'All' },
              { key: 'polymarket', label: 'Polymarket', icon: Search },
              { key: 'twitter', label: 'Twitter', icon: MessageCircle },
              { key: 'youtube', label: 'YouTube', icon: Youtube }
            ].map(({ key, label, icon: Icon }) => (
              <button
                key={key}
                onClick={() => setFilter(key)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.4rem',
                  padding: '0.4rem 0.75rem',
                  border: 'none',
                  borderRadius: '6px',
                  fontSize: '0.8rem',
                  fontWeight: 500,
                  cursor: 'pointer',
                  background: filter === key 
                    ? 'linear-gradient(135deg, #8b5cf6, #6d28d9)' 
                    : 'var(--bg-tertiary)',
                  color: filter === key ? 'white' : 'var(--text-secondary)'
                }}
              >
                {Icon && <Icon size={12} />}
                {label}
              </button>
            ))}
          </div>

          {/* History List */}
          <div style={{
            maxHeight: '300px',
            overflowY: 'auto'
          }}>
            {filteredHistory.length === 0 ? (
              <div style={{
                padding: '2rem',
                textAlign: 'center',
                color: 'var(--text-muted)'
              }}>
                <Clock size={32} style={{ marginBottom: '0.5rem', opacity: 0.5 }} />
                <p style={{ fontSize: '0.85rem' }}>No query history yet</p>
                <p style={{ fontSize: '0.75rem', marginTop: '0.25rem' }}>
                  Your searches will appear here
                </p>
              </div>
            ) : (
              filteredHistory.map((item) => (
                <div
                  key={item.id}
                  onClick={() => onSelectQuery(item)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.75rem',
                    padding: '0.75rem 1.25rem',
                    borderBottom: '1px solid var(--border-color)',
                    cursor: 'pointer',
                    transition: 'background 0.15s'
                  }}
                  onMouseOver={(e) => e.currentTarget.style.background = 'var(--bg-tertiary)'}
                  onMouseOut={(e) => e.currentTarget.style.background = 'transparent'}
                >
                  {/* Icon */}
                  <div style={{
                    width: '32px',
                    height: '32px',
                    borderRadius: '8px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    background: item.type === 'polymarket' 
                      ? 'rgba(139, 92, 246, 0.15)' 
                      : item.type === 'youtube'
                      ? 'rgba(255, 0, 0, 0.15)'
                      : 'rgba(0, 212, 255, 0.15)',
                    color: item.type === 'polymarket' 
                      ? '#8b5cf6' 
                      : item.type === 'youtube'
                      ? '#ff0000'
                      : '#00d4ff',
                    flexShrink: 0
                  }}>
                    {item.type === 'polymarket' ? <Search size={14} /> : item.type === 'youtube' ? <Youtube size={14} /> : <MessageCircle size={14} />}
                  </div>

                  {/* Content */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{
                      fontSize: '0.85rem',
                      fontWeight: 500,
                      color: 'var(--text-primary)',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis'
                    }}>
                      {getQuerySummary(item)}
                    </div>
                    {item.type === 'twitter' && item.query.topic && (
                      <div style={{
                        fontSize: '0.75rem',
                        color: 'var(--text-muted)',
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis'
                      }}>
                        Topic: {item.query.topic}
                      </div>
                    )}
                  </div>

                  {/* Timestamp */}
                  <div style={{
                    fontSize: '0.7rem',
                    color: 'var(--text-muted)',
                    whiteSpace: 'nowrap'
                  }}>
                    {formatDate(item.timestamp)}
                  </div>

                  {/* Delete Button */}
                  <button
                    onClick={(e) => handleDelete(item.id, e)}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: 'var(--text-muted)',
                      cursor: 'pointer',
                      padding: '0.25rem',
                      opacity: 0.5,
                      transition: 'opacity 0.15s'
                    }}
                    onMouseOver={(e) => e.currentTarget.style.opacity = 1}
                    onMouseOut={(e) => e.currentTarget.style.opacity = 0.5}
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
              ))
            )}
          </div>
        </>
      )}
    </div>
  )
}


import { useState, useEffect } from 'react'
import { FileText, Download, Trash2, FolderOpen, ChevronDown, ChevronUp, Search, MessageCircle, Calendar } from 'lucide-react'

const SAVED_FILES_KEY = 'sourcer_saved_files'
const MAX_SAVED_FILES = 100

/**
 * Get saved files from localStorage
 */
export const getSavedFiles = () => {
  try {
    const saved = localStorage.getItem(SAVED_FILES_KEY)
    return saved ? JSON.parse(saved) : []
  } catch {
    return []
  }
}

/**
 * Save a markdown file to storage
 */
export const saveMarkdownFile = (filename, content, type, metadata = {}) => {
  const files = getSavedFiles()
  
  const newFile = {
    id: Date.now(),
    filename,
    content,
    type, // 'polymarket-search', 'polymarket-details', 'twitter'
    metadata, // Additional info like keyword, handles, etc.
    savedAt: new Date().toISOString(),
    size: new Blob([content]).size
  }
  
  // Add to beginning
  const updated = [newFile, ...files].slice(0, MAX_SAVED_FILES)
  localStorage.setItem(SAVED_FILES_KEY, JSON.stringify(updated))
  
  return updated
}

/**
 * Delete a saved file
 */
export const deleteSavedFile = (id) => {
  const files = getSavedFiles()
  const updated = files.filter(f => f.id !== id)
  localStorage.setItem(SAVED_FILES_KEY, JSON.stringify(updated))
  return updated
}

/**
 * Clear all saved files
 */
export const clearAllSavedFiles = () => {
  localStorage.removeItem(SAVED_FILES_KEY)
}

/**
 * Download a file
 */
export const downloadFile = (filename, content) => {
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename.endsWith('.md') ? filename : `${filename}.md`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

/**
 * Format file size
 */
const formatSize = (bytes) => {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

/**
 * SavedFiles component - displays and manages saved markdown files
 */
export default function SavedFiles() {
  const [files, setFiles] = useState([])
  const [filter, setFilter] = useState('all') // 'all', 'polymarket', 'twitter'
  const [expanded, setExpanded] = useState(true)
  const [previewFile, setPreviewFile] = useState(null)

  useEffect(() => {
    setFiles(getSavedFiles())
  }, [])

  const handleDelete = (id, e) => {
    e.stopPropagation()
    const updated = deleteSavedFile(id)
    setFiles(updated)
  }

  const handleClearAll = () => {
    if (confirm('Delete all saved files? This cannot be undone.')) {
      clearAllSavedFiles()
      setFiles([])
    }
  }

  const handleDownload = (file, e) => {
    e.stopPropagation()
    downloadFile(file.filename, file.content)
  }

  const filteredFiles = files.filter(file => {
    if (filter === 'all') return true
    if (filter === 'polymarket') return file.type?.startsWith('polymarket')
    if (filter === 'twitter') return file.type === 'twitter'
    return true
  })

  const formatDate = (timestamp) => {
    const date = new Date(timestamp)
    const now = new Date()
    const diff = now - date
    
    if (diff < 60000) return 'Just now'
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`
    if (diff < 604800000) return `${Math.floor(diff / 86400000)}d ago`
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }

  const getTypeIcon = (type) => {
    if (type?.startsWith('polymarket')) return <Search size={14} />
    if (type === 'twitter') return <MessageCircle size={14} />
    return <FileText size={14} />
  }

  const getTypeColor = (type) => {
    if (type?.startsWith('polymarket')) return '#8b5cf6'
    if (type === 'twitter') return '#00d4ff'
    return 'var(--text-muted)'
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
          <FolderOpen size={18} style={{ color: 'var(--accent-purple)' }} />
          <h3 style={{ 
            fontSize: '0.9rem', 
            fontWeight: 600,
            color: 'var(--text-primary)'
          }}>
            Saved Reports
          </h3>
          <span style={{
            background: 'var(--bg-tertiary)',
            padding: '0.15rem 0.5rem',
            borderRadius: '10px',
            fontSize: '0.75rem',
            color: 'var(--text-muted)'
          }}>
            {files.length}
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          {files.length > 0 && expanded && (
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
              title="Delete all saved files"
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
              { key: 'twitter', label: 'Twitter', icon: MessageCircle }
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

          {/* Files List */}
          <div style={{
            maxHeight: '350px',
            overflowY: 'auto'
          }}>
            {filteredFiles.length === 0 ? (
              <div style={{
                padding: '2rem',
                textAlign: 'center',
                color: 'var(--text-muted)'
              }}>
                <FileText size={32} style={{ marginBottom: '0.5rem', opacity: 0.5 }} />
                <p style={{ fontSize: '0.85rem' }}>No saved reports yet</p>
                <p style={{ fontSize: '0.75rem', marginTop: '0.25rem' }}>
                  Click "Save MD" on any result to save it here
                </p>
              </div>
            ) : (
              filteredFiles.map((file) => (
                <div
                  key={file.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.75rem',
                    padding: '0.75rem 1.25rem',
                    borderBottom: '1px solid var(--border-color)',
                    cursor: 'pointer',
                    transition: 'background 0.15s'
                  }}
                  onClick={() => setPreviewFile(previewFile?.id === file.id ? null : file)}
                  onMouseOver={(e) => e.currentTarget.style.background = 'var(--bg-tertiary)'}
                  onMouseOut={(e) => e.currentTarget.style.background = 'transparent'}
                >
                  {/* Icon */}
                  <div style={{
                    width: '36px',
                    height: '36px',
                    borderRadius: '8px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    background: `${getTypeColor(file.type)}15`,
                    color: getTypeColor(file.type),
                    flexShrink: 0
                  }}>
                    {getTypeIcon(file.type)}
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
                      {file.filename}
                    </div>
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.75rem',
                      fontSize: '0.75rem',
                      color: 'var(--text-muted)',
                      marginTop: '0.2rem'
                    }}>
                      <span style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                        <Calendar size={10} />
                        {formatDate(file.savedAt)}
                      </span>
                      <span>{formatSize(file.size)}</span>
                    </div>
                  </div>

                  {/* Actions */}
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <button
                      onClick={(e) => handleDownload(file, e)}
                      style={{
                        background: 'var(--bg-tertiary)',
                        border: 'none',
                        color: 'var(--accent-cyan)',
                        cursor: 'pointer',
                        padding: '0.4rem',
                        borderRadius: '6px',
                        display: 'flex',
                        alignItems: 'center'
                      }}
                      title="Download file"
                    >
                      <Download size={14} />
                    </button>
                    <button
                      onClick={(e) => handleDelete(file.id, e)}
                      style={{
                        background: 'var(--bg-tertiary)',
                        border: 'none',
                        color: 'var(--text-muted)',
                        cursor: 'pointer',
                        padding: '0.4rem',
                        borderRadius: '6px',
                        display: 'flex',
                        alignItems: 'center'
                      }}
                      title="Delete file"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Preview Panel */}
          {previewFile && (
            <div style={{
              borderTop: '1px solid var(--border-color)',
              padding: '1rem 1.25rem',
              background: 'var(--bg-tertiary)'
            }}>
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '0.75rem'
              }}>
                <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                  Preview: {previewFile.filename}
                </span>
                <button
                  onClick={() => downloadFile(previewFile.filename, previewFile.content)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.4rem',
                    background: 'linear-gradient(135deg, #00d4ff, #0099cc)',
                    border: 'none',
                    color: 'white',
                    padding: '0.4rem 0.75rem',
                    borderRadius: '6px',
                    fontSize: '0.75rem',
                    fontWeight: 500,
                    cursor: 'pointer'
                  }}
                >
                  <Download size={12} />
                  Download
                </button>
              </div>
              <pre style={{
                background: 'var(--bg-primary)',
                border: '1px solid var(--border-color)',
                borderRadius: '8px',
                padding: '1rem',
                fontSize: '0.75rem',
                color: 'var(--text-secondary)',
                maxHeight: '200px',
                overflowY: 'auto',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                margin: 0,
                fontFamily: 'JetBrains Mono, monospace'
              }}>
                {previewFile.content.slice(0, 2000)}
                {previewFile.content.length > 2000 && '\n\n... (truncated)'}
              </pre>
            </div>
          )}
        </>
      )}
    </div>
  )
}


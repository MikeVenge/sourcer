import { useState, useEffect } from 'react'
import { BookOpen, Check, AlertCircle, Loader2 } from 'lucide-react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function NotebookLMExport({ content, sourceName, sourceType, contentType = 'text', url = null }) {
  const [isOpen, setIsOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState(null)
  const [availableNotebooks, setAvailableNotebooks] = useState([])
  const [selectedNotebooks, setSelectedNotebooks] = useState([])
  const [loadingNotebooks, setLoadingNotebooks] = useState(false)

  // Fetch available notebooks when modal opens
  useEffect(() => {
    if (isOpen && availableNotebooks.length === 0) {
      fetchAvailableNotebooks()
    }
  }, [isOpen])

  const fetchAvailableNotebooks = async () => {
    setLoadingNotebooks(true)
    try {
      const response = await fetch(`${API_URL}/notebooklm/notebooks`)
      if (response.ok) {
        const data = await response.json()
        setAvailableNotebooks(data.notebooks || [])
      } else {
        console.error('Failed to fetch notebooks')
      }
    } catch (err) {
      console.error('Error fetching notebooks:', err)
    } finally {
      setLoadingNotebooks(false)
    }
  }

  const handleNotebookToggle = (notebookId) => {
    setSelectedNotebooks(prev => {
      if (prev.includes(notebookId)) {
        return prev.filter(id => id !== notebookId)
      } else {
        return [...prev, notebookId]
      }
    })
  }

  const handleExport = async () => {
    if (selectedNotebooks.length === 0) {
      setError('Please select at least one notebook')
      return
    }

    setLoading(true)
    setError(null)

    try {
      // For YouTube videos, fetch transcript if content is empty
      let contentToSend = content
      if (contentType === 'youtube' && (!content || content.trim() === '') && url) {
        try {
          // Show loading message for transcript fetch
          const transcriptResponse = await fetch(`${API_URL}/youtube/transcript`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url: url })
          })
          
          if (transcriptResponse.ok) {
            const transcriptData = await transcriptResponse.json()
            const transcriptText = transcriptData.transcript
              .map(segment => segment.text)
              .join('\n\n')
            // Include URL in content so it's clear where it came from
            contentToSend = `YouTube Video: ${url}\n\n${transcriptText}`
          } else {
            const errorData = await transcriptResponse.json().catch(() => ({}))
            throw new Error(errorData.detail || 'Failed to fetch transcript')
          }
        } catch (transcriptError) {
          throw new Error(`Failed to fetch transcript: ${transcriptError.message}`)
        }
      }

      const response = await fetch(`${API_URL}/notebooklm/add-source`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          source_name: sourceName,
          content: contentToSend,
          source_type: sourceType,
          content_type: contentType === 'youtube' ? 'text' : contentType, // Send as text when we have transcript
          url: url,
          notebook_ids: selectedNotebooks  // Send selected notebook IDs
        })
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to export to NotebookLM')
      }

      const data = await response.json()
      setSuccess(true)
      
      setTimeout(() => {
        handleClose()
      }, 3000)

    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleClose = () => {
    setIsOpen(false)
    setError(null)
    setSuccess(false)
    setSelectedNotebooks([])
  }

  if (!isOpen) {
    return (
      <button 
        className="save-btn"
        onClick={() => setIsOpen(true)}
        title="Export to NotebookLM"
      >
        <BookOpen size={16} />
        Save LM
      </button>
    )
  }

  return (
    <div className="notebooklm-modal-overlay" onClick={handleClose}>
      <div className="notebooklm-modal" onClick={(e) => e.stopPropagation()}>
        <div className="notebooklm-modal-header">
          <BookOpen size={24} />
          <h3>Export to NotebookLM</h3>
        </div>

        <div className="notebooklm-modal-body">
          <p className="notebooklm-info">
            Select one or more notebooks to send this content to.
          </p>

          <div className="form-group">
            <label>Source Name</label>
            <input
              type="text"
              className="form-input"
              value={sourceName}
              readOnly
            />
            <p className="form-hint">
              This will be the name of the source in NotebookLM
            </p>
          </div>

          <div className="form-group">
            <label>Select Notebooks</label>
            {loadingNotebooks ? (
              <div style={{ padding: '1rem', textAlign: 'center' }}>
                <Loader2 size={20} className="spin" />
                <p style={{ marginTop: '0.5rem', fontSize: '14px', color: '#999' }}>Loading notebooks...</p>
              </div>
            ) : availableNotebooks.length > 0 ? (
              <div style={{ 
                maxHeight: '300px', 
                overflowY: 'auto',
                border: '1px solid var(--border-color)',
                borderRadius: '8px',
                padding: '0.75rem'
              }}>
                {availableNotebooks.map((notebook) => (
                  <label
                    key={notebook.id}
                    style={{
                      display: 'flex',
                      alignItems: 'flex-start',
                      padding: '0.75rem',
                      marginBottom: '0.5rem',
                      cursor: 'pointer',
                      borderRadius: '6px',
                      backgroundColor: selectedNotebooks.includes(notebook.id) ? 'rgba(59, 130, 246, 0.1)' : 'transparent',
                      border: selectedNotebooks.includes(notebook.id) ? '1px solid rgba(59, 130, 246, 0.3)' : '1px solid transparent',
                      transition: 'all 0.2s'
                    }}
                    onMouseEnter={(e) => {
                      if (!selectedNotebooks.includes(notebook.id)) {
                        e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.05)'
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!selectedNotebooks.includes(notebook.id)) {
                        e.currentTarget.style.backgroundColor = 'transparent'
                      }
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={selectedNotebooks.includes(notebook.id)}
                      onChange={() => handleNotebookToggle(notebook.id)}
                      style={{
                        marginRight: '0.75rem',
                        marginTop: '2px',
                        cursor: 'pointer'
                      }}
                    />
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: '500', marginBottom: '4px' }}>
                        {notebook.name}
                      </div>
                      {notebook.id && (
                        <div style={{ fontSize: '11px', color: '#999', fontFamily: 'monospace' }}>
                          ID: {notebook.id}
                        </div>
                      )}
                    </div>
                  </label>
                ))}
              </div>
            ) : (
              <div style={{ padding: '1rem', textAlign: 'center', color: '#999' }}>
                No notebooks available
              </div>
            )}
          </div>

          {error && (
            <div className="notebooklm-error">
              <AlertCircle size={16} />
              {error}
            </div>
          )}

          {success && (
            <div className="notebooklm-success">
              <Check size={16} />
              <div>
                <div style={{ fontWeight: 'bold', marginBottom: '8px' }}>
                  Successfully exported to NotebookLM!
                </div>
                <div style={{ fontSize: '13px', color: '#999' }}>
                  Sent to {selectedNotebooks.length} notebook{selectedNotebooks.length > 1 ? 's' : ''}
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="notebooklm-modal-footer">
          <button 
            className="cancel-btn"
            onClick={handleClose}
            disabled={loading}
          >
            Cancel
          </button>
          <button 
            className="submit-btn"
            onClick={handleExport}
            disabled={loading || success || selectedNotebooks.length === 0}
          >
            {loading ? (
              <>
                <Loader2 size={16} className="spin" />
                Exporting...
              </>
            ) : success ? (
              <>
                <Check size={16} />
                Done!
              </>
            ) : (
              <>
                <BookOpen size={16} />
                Export
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}

import { useState, useEffect } from 'react'
import { BookOpen, Check, AlertCircle, Loader2, X } from 'lucide-react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function NotebookLMExport({ content, sourceName, sourceType, contentType = 'text', url = null }) {
  console.log('[NotebookLMExport] Component rendered with props:', {
    sourceName,
    sourceType,
    contentType,
    contentLength: content?.length || 0,
    url
  })
  
  const [isOpen, setIsOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState(null)
  const [availableNotebooks, setAvailableNotebooks] = useState([])
  const [selectedNotebooks, setSelectedNotebooks] = useState([])
  const [loadingNotebooks, setLoadingNotebooks] = useState(false)
  const [notebooks, setNotebooks] = useState([]) // For showing results after auto-classification

  // Only show notebook selection UI for YouTube
  const showNotebookSelection = contentType === 'youtube'
  
  console.log('[NotebookLMExport] showNotebookSelection:', showNotebookSelection)

  // Fetch available notebooks when modal opens (only for YouTube)
  useEffect(() => {
    if (isOpen && showNotebookSelection) {
      console.log('[NotebookLMExport] Modal opened, checking if fetch needed...', { 
        isOpen, 
        showNotebookSelection, 
        availableNotebooksLength: availableNotebooks.length,
        loadingNotebooks,
        availableNotebooks
      })
      // Only fetch if not already loading and we don't have notebooks yet
      if (!loadingNotebooks && (!availableNotebooks || availableNotebooks.length === 0)) {
        console.log('[NotebookLMExport] Triggering fetch...')
        fetchAvailableNotebooks()
      } else {
        console.log('[NotebookLMExport] Skipping fetch - already have notebooks or loading')
      }
    }
  }, [isOpen, showNotebookSelection])

  const fetchAvailableNotebooks = async () => {
    setLoadingNotebooks(true)
    try {
      console.log('[NotebookLMExport] Fetching from:', `${API_URL}/notebooklm/notebooks`)
      const response = await fetch(`${API_URL}/notebooklm/notebooks`)
      console.log('[NotebookLMExport] Response status:', response.status)
      if (response.ok) {
        const data = await response.json()
        console.log('[NotebookLMExport] Received notebooks:', data)
        setAvailableNotebooks(data.notebooks || [])
        console.log('[NotebookLMExport] Set availableNotebooks:', data.notebooks || [])
      } else {
        const errorText = await response.text().catch(() => '')
        console.error('Failed to fetch notebooks:', response.status, errorText)
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
    console.log('[NotebookLMExport] handleExport called')
    // For YouTube, require notebook selection
    if (showNotebookSelection && selectedNotebooks.length === 0) {
      setError('Please select at least one notebook')
      return
    }

    console.log('[NotebookLMExport] Starting export...')
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
            // Include URL in content so it's clear where it's clear where it came from
            contentToSend = `YouTube Video: ${url}\n\n${transcriptText}`
          } else {
            const errorData = await transcriptResponse.json().catch(() => ({}))
            throw new Error(errorData.detail || 'Failed to fetch transcript')
          }
        } catch (transcriptError) {
          throw new Error(`Failed to fetch transcript: ${transcriptError.message}`)
        }
      }

      console.log('[NotebookLMExport] Sending to backend:', {
        source_name: sourceName,
        content_length: contentToSend?.length || 0,
        content_preview: contentToSend?.substring(0, 200) || '(empty)',
        source_type: sourceType,
        content_type: contentType, // Keep original content_type (youtube, text, web)
        url: url,
        notebook_ids: showNotebookSelection ? selectedNotebooks : undefined
      })

      const requestBody = {
        source_name: sourceName,
        content: contentToSend, // Still send content for classification, but backend will use URL for YouTube
        source_type: sourceType,
        content_type: contentType, // Keep original content_type so backend knows to use webContent for YouTube
        url: url,
        notebook_ids: showNotebookSelection ? selectedNotebooks : undefined
      }
      
      console.log('[NotebookLMExport] Making fetch request to:', `${API_URL}/notebooklm/add-source`)
      
      let response
      try {
        response = await fetch(`${API_URL}/notebooklm/add-source`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(requestBody)
        })
      } catch (fetchError) {
        console.error('[NotebookLMExport] Fetch failed:', fetchError)
        throw new Error(`Network error: ${fetchError.message}. Make sure the backend is running at ${API_URL}`)
      }

      console.log('[NotebookLMExport] Response status:', response.status)
      
      if (!response.ok) {
        let errorMessage = `Server error: ${response.status}`
        try {
          const errorData = await response.json()
          errorMessage = errorData.detail || errorMessage
        } catch (e) {
          // Response might not be JSON
          const textError = await response.text().catch(() => '')
          if (textError) errorMessage = textError.substring(0, 200)
        }
        throw new Error(errorMessage)
      }

      const data = await response.json()
      
      console.log('[NotebookLMExport] Response data:', data)
      
      // Check if classification failed or returned no notebooks
      if (!data.success || (data.classified_notebooks && data.classified_notebooks.length === 0)) {
        throw new Error(data.message || 'Content did not match any investment-theme notebooks')
      }
      
      // For auto-classified content (Twitter/Polymarket/Reddit), show which notebooks were selected
      if (!showNotebookSelection && data.classified_notebooks && data.classified_notebooks.length > 0) {
        const notebookMapping = data.notebook_mapping || {}
        const notebookResults = data.classified_notebooks.map(name => ({
          notebook: name,
          notebook_id: notebookMapping[name] || null,
          success: true
        }))
        console.log('[NotebookLMExport] Setting notebooks:', notebookResults)
        setNotebooks(notebookResults)
      }
      
      setSuccess(true)
      
      // Don't auto-close for Twitter/Polymarket so user can see the results
      if (showNotebookSelection) {
        setTimeout(() => {
          handleClose()
        }, 3000)
      }

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
    setNotebooks([])
    // Reset availableNotebooks so we fetch fresh data next time
    setAvailableNotebooks([])
  }

  // For Twitter/Polymarket, directly export without showing modal
  const handleClick = () => {
    console.log('[NotebookLMExport] handleClick called', { showNotebookSelection, loading, success })
    if (showNotebookSelection) {
      // YouTube: Show notebook selection modal
      console.log('[NotebookLMExport] Opening modal for YouTube')
      setIsOpen(true)
    } else {
      // Twitter/Polymarket: Direct export with auto-classification
      console.log('[NotebookLMExport] Calling handleExport for Twitter/Polymarket')
      handleExport()
    }
  }

  if (!isOpen && showNotebookSelection) {
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

  // For Twitter/Polymarket, show button that directly exports
  if (!showNotebookSelection) {
    return (
      <>
        <button 
          className="save-btn"
          onClick={(e) => {
            console.log('[NotebookLMExport] Button clicked!', { loading, success, disabled: loading || success })
            e.preventDefault()
            e.stopPropagation()
            handleClick()
          }}
          disabled={loading || success}
          title="Export to NotebookLM (Auto-classified)"
        >
          {loading ? (
            <Loader2 size={16} className="spin" />
          ) : success ? (
            <Check size={16} />
          ) : (
            <BookOpen size={16} />
          )}
          Save LM
        </button>
        
        {/* Loading modal */}
        {loading && (
          <div 
            className="notebooklm-modal-overlay"
            style={{ cursor: 'wait' }}
          >
            <div 
              className="notebooklm-modal" 
              style={{ maxWidth: '400px', textAlign: 'center' }}
            >
              <div style={{ marginBottom: '1.5rem' }}>
                <Loader2 size={48} className="spin" style={{ color: 'var(--primary-color)' }} />
              </div>
              <h3 style={{ marginBottom: '1rem' }}>Classifying Content...</h3>
              <p style={{ color: 'var(--text-muted)', fontSize: '14px', lineHeight: '1.6' }}>
                Using AI to analyze your content and determine the best investment-theme notebooks.
                <br />
                <br />
                This may take 20-30 seconds.
              </p>
            </div>
          </div>
        )}
        
        {/* Error modal */}
        {error && (
          <div 
            className="notebooklm-modal-overlay" 
            onClick={() => setError(null)}
          >
            <div 
              className="notebooklm-modal" 
              onClick={(e) => e.stopPropagation()}
              style={{ maxWidth: '500px' }}
            >
              <div className="notebooklm-modal-header">
                <AlertCircle size={24} style={{ color: '#ef4444' }} />
                <h3>Export Failed</h3>
              </div>
              <div className="notebooklm-modal-body">
                <p style={{ color: 'var(--text-secondary)', fontSize: '14px', lineHeight: '1.6' }}>
                  {error}
                </p>
              </div>
              <div className="notebooklm-modal-footer">
                <button 
                  className="submit-btn"
                  onClick={() => setError(null)}
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}
        
        {/* Success modal */}
        {success && notebooks.length > 0 && (
          <div 
            className="notebooklm-modal-overlay" 
            onClick={() => {
              setSuccess(false)
              setNotebooks([])
            }}
          >
            <div 
              className="notebooklm-modal" 
              onClick={(e) => e.stopPropagation()}
              style={{ maxWidth: '500px' }}
            >
              <div className="notebooklm-modal-header">
                <Check size={24} style={{ color: '#10b981' }} />
                <h3>Successfully Exported!</h3>
              </div>
              <div className="notebooklm-modal-body">
                <p className="notebooklm-info">
                  Content was auto-classified and sent to the following notebooks:
                </p>
                <ul style={{ margin: '1rem 0', paddingLeft: '1.5rem', listStyleType: 'disc' }}>
                  {notebooks.map((notebook, index) => (
                    <li key={index} style={{ marginBottom: '0.5rem', fontSize: '14px' }}>
                      <strong>{notebook.notebook}</strong>
                      {notebook.notebook_id && (
                        <div style={{ fontSize: '11px', color: '#999', fontFamily: 'monospace', marginTop: '2px' }}>
                          ID: {notebook.notebook_id}
                        </div>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
              <div className="notebooklm-modal-footer">
                <button 
                  className="submit-btn"
                  onClick={() => {
                    setSuccess(false)
                    setNotebooks([])
                  }}
                >
                  <Check size={16} />
                  Done
                </button>
              </div>
            </div>
          </div>
        )}
      </>
    )
  }

  return (
    <div className="notebooklm-modal-overlay" onClick={handleClose}>
      <div className="notebooklm-modal" onClick={(e) => e.stopPropagation()}>
        <div className="notebooklm-modal-header">
          <BookOpen size={24} />
          <h3>Export to NotebookLM</h3>
          <button
            onClick={handleClose}
            style={{
              marginLeft: 'auto',
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              padding: '0.25rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
            title="Close"
          >
            <X size={20} />
          </button>
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

          {showNotebookSelection && (
            <div className="form-group">
              <label>Select Notebooks</label>
              {(() => {
                console.log('[NotebookLMExport] Rendering notebooks list:', {
                  loadingNotebooks,
                  availableNotebooksLength: availableNotebooks.length,
                  availableNotebooks
                })
                return null
              })()}
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
          )}

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
                {showNotebookSelection ? (
                  <div style={{ fontSize: '13px', color: '#999' }}>
                    Sent to {selectedNotebooks.length} notebook{selectedNotebooks.length > 1 ? 's' : ''}
                  </div>
                ) : notebooks.length > 0 ? (
                  <div style={{ marginTop: '12px' }}>
                    <div style={{ fontSize: '14px', fontWeight: '500', marginBottom: '6px' }}>
                      Auto-classified and sent to {notebooks.length} notebook{notebooks.length > 1 ? 's' : ''}:
                    </div>
                    <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '13px', listStyleType: 'disc' }}>
                      {notebooks.map((notebook, index) => (
                        <li key={index} style={{ marginBottom: '4px' }}>
                          {notebook.notebook}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : (
                  <div style={{ fontSize: '13px', color: '#999' }}>
                    Content has been exported
                  </div>
                )}
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












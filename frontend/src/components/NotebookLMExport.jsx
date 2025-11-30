import { useState } from 'react'
import { BookOpen, Check, AlertCircle, Loader2 } from 'lucide-react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function NotebookLMExport({ content, sourceName, contentType = 'text', url = null }) {
  const [isOpen, setIsOpen] = useState(false)
  const [notebookId, setNotebookId] = useState('')
  const [accessToken, setAccessToken] = useState('')
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState(null)

  const handleExport = async () => {
    if (!notebookId.trim() || !accessToken.trim()) {
      setError('Please enter both Notebook ID and Access Token')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const response = await fetch(`${API_URL}/notebooklm/add-source`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          notebook_id: notebookId,
          source_name: sourceName,
          content: content,
          content_type: contentType,
          url: url,
          access_token: accessToken
        })
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to export to NotebookLM')
      }

      setSuccess(true)
      setTimeout(() => {
        setSuccess(false)
        setIsOpen(false)
      }, 2000)

    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  if (!isOpen) {
    return (
      <button 
        className="save-btn notebooklm-btn"
        onClick={() => setIsOpen(true)}
        title="Export to NotebookLM"
      >
        <BookOpen size={16} />
      </button>
    )
  }

  return (
    <div className="notebooklm-modal-overlay" onClick={() => setIsOpen(false)}>
      <div className="notebooklm-modal" onClick={(e) => e.stopPropagation()}>
        <div className="notebooklm-modal-header">
          <BookOpen size={24} />
          <h3>Export to NotebookLM</h3>
        </div>

        <div className="notebooklm-modal-body">
          <p className="notebooklm-info">
            Send this content to your Google NotebookLM notebook.
          </p>

          <div className="form-group">
            <label>Notebook ID</label>
            <input
              type="text"
              className="form-input"
              placeholder="Enter your NotebookLM notebook ID"
              value={notebookId}
              onChange={(e) => setNotebookId(e.target.value)}
            />
            <p className="form-hint">
              Find this in your NotebookLM URL: notebooklm.google.com/notebook/NOTEBOOK_ID
            </p>
          </div>

          <div className="form-group">
            <label>Google Cloud Access Token</label>
            <input
              type="password"
              className="form-input"
              placeholder="Paste your access token"
              value={accessToken}
              onChange={(e) => setAccessToken(e.target.value)}
            />
            <p className="form-hint">
              Get token via: <code>gcloud auth print-access-token</code>
            </p>
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
              Successfully exported to NotebookLM!
            </div>
          )}
        </div>

        <div className="notebooklm-modal-footer">
          <button 
            className="cancel-btn"
            onClick={() => setIsOpen(false)}
          >
            Cancel
          </button>
          <button 
            className="submit-btn"
            onClick={handleExport}
            disabled={loading || success}
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


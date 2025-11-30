import { useState } from 'react'
import { BookOpen, Check, AlertCircle, Loader2 } from 'lucide-react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function NotebookLMExport({ content, sourceName, sourceType, contentType = 'text', url = null }) {
  const [isOpen, setIsOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState(null)

  const handleExport = async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await fetch(`${API_URL}/notebooklm/add-source`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          source_name: sourceName,
          content: content,
          source_type: sourceType,
          content_type: contentType,
          url: url
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


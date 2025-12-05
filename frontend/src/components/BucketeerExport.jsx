import { useState } from 'react'
import { Box, Check, AlertCircle, Loader2 } from 'lucide-react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function BucketeerExport({ content, sourceName, sourceType, contentType = 'text', url = null }) {
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState(null)
  const [showModal, setShowModal] = useState(false)

  const handleExport = async () => {
    setLoading(true)
    setError(null)
    setShowModal(true)

    try {
      // For YouTube videos, fetch transcript if content is empty
      let contentToSend = content
      if (contentType === 'youtube' && (!content || content.trim() === '') && url) {
        try {
          const transcriptResponse = await fetch(`${API_URL}/youtube/transcript`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url })
          })
          
          if (!transcriptResponse.ok) {
            throw new Error('Failed to fetch YouTube transcript')
          }
          
          const transcriptData = await transcriptResponse.json()
          // Properly serialize transcript array to text
          let transcriptText = ''
          if (transcriptData.transcript && Array.isArray(transcriptData.transcript)) {
            // Extract text from each segment and join with spaces
            transcriptText = transcriptData.transcript
              .map(segment => segment.text || '')
              .filter(text => text.trim())
              .join(' ')
          } else if (typeof transcriptData.transcript === 'string') {
            transcriptText = transcriptData.transcript
          }
          // Combine URL and transcript for context
          contentToSend = `YouTube URL: ${url}\n\nTranscript:\n${transcriptText}`
        } catch (transcriptError) {
          console.error('Error fetching transcript:', transcriptError)
          // Fallback to just URL if transcript fails
          contentToSend = `YouTube URL: ${url}`
        }
      }

      // Prepare content with source information
      const contentWithMetadata = `Source: ${sourceName || 'Unknown'}\nType: ${sourceType || contentType}\n${url ? `URL: ${url}\n\n` : ''}${contentToSend || ''}`

      const response = await fetch(`${API_URL}/bucketeer/add-content`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          content: contentWithMetadata,
          source_name: sourceName,
          source_type: sourceType,
          content_type: contentType,
          url: url
        })
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ message: 'Unknown error' }))
        throw new Error(errorData.message || `HTTP ${response.status}`)
      }

      const data = await response.json()
      
      if (data.success) {
        setSuccess(true)
        // Auto-close modal after 3 seconds
        setTimeout(() => {
          setShowModal(false)
          setSuccess(false)
        }, 3000)
      } else {
        throw new Error(data.message || 'Failed to export to Bucketeer')
      }
    } catch (error) {
      console.error('Bucketeer export error:', error)
      setError(error.message || 'Failed to export to Bucketeer')
    } finally {
      setLoading(false)
    }
  }

  const handleClose = () => {
    setShowModal(false)
    setSuccess(false)
    setError(null)
  }

  return (
    <>
      <button
        onClick={handleExport}
        disabled={loading || success}
        className="save-btn"
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '0.5rem',
          padding: '0.5rem 1rem',
          backgroundColor: 'var(--accent-purple)',
          color: 'white',
          border: 'none',
          borderRadius: '8px',
          cursor: loading || success ? 'not-allowed' : 'pointer',
          opacity: loading || success ? 0.6 : 1,
          fontSize: '0.9rem',
          fontWeight: 500
        }}
      >
        {loading ? (
          <>
            <Loader2 size={16} className="spinning" />
            Sending to BT...
          </>
        ) : success ? (
          <>
            <Check size={16} />
            Sent to BT!
          </>
        ) : (
          <>
            <Box size={16} />
            Save BT
          </>
        )}
      </button>

      {/* Modal for loading/success/error states */}
      {showModal && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.7)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 10000
          }}
          onClick={handleClose}
        >
          <div
            style={{
              backgroundColor: 'var(--bg-primary)',
              borderRadius: '12px',
              padding: '2rem',
              maxWidth: '500px',
              width: '90%',
              boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {loading && (
              <div style={{ textAlign: 'center' }}>
                <Loader2 size={48} className="spinning" style={{ color: 'var(--accent-purple)', marginBottom: '1rem' }} />
                <h3 style={{ marginBottom: '0.5rem' }}>Sending to Bucketeer...</h3>
                <p style={{ color: 'var(--text-secondary)' }}>
                  Content is being automatically classified and added to buckets.
                </p>
              </div>
            )}

            {success && (
              <div style={{ textAlign: 'center' }}>
                <Check size={48} style={{ color: 'var(--accent-green)', marginBottom: '1rem' }} />
                <h3 style={{ marginBottom: '0.5rem' }}>Success!</h3>
                <p style={{ color: 'var(--text-secondary)' }}>
                  Content has been sent to Bucketeer and automatically classified.
                </p>
                <button
                  onClick={handleClose}
                  style={{
                    marginTop: '1rem',
                    padding: '0.5rem 1.5rem',
                    backgroundColor: 'var(--accent-purple)',
                    color: 'white',
                    border: 'none',
                    borderRadius: '8px',
                    cursor: 'pointer'
                  }}
                >
                  Done
                </button>
              </div>
            )}

            {error && (
              <div style={{ textAlign: 'center' }}>
                <AlertCircle size={48} style={{ color: 'var(--accent-red)', marginBottom: '1rem' }} />
                <h3 style={{ marginBottom: '0.5rem' }}>Error</h3>
                <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem' }}>{error}</p>
                <button
                  onClick={handleClose}
                  style={{
                    padding: '0.5rem 1.5rem',
                    backgroundColor: 'var(--accent-red)',
                    color: 'white',
                    border: 'none',
                    borderRadius: '8px',
                    cursor: 'pointer'
                  }}
                >
                  Close
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  )
}


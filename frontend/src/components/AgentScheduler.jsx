import { useState, useEffect } from 'react'
import { Calendar, Clock, X } from 'lucide-react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const DAYS_OF_WEEK = [
  { value: '0', label: 'Monday' },
  { value: '1', label: 'Tuesday' },
  { value: '2', label: 'Wednesday' },
  { value: '3', label: 'Thursday' },
  { value: '4', label: 'Friday' },
  { value: '5', label: 'Saturday' },
  { value: '6', label: 'Sunday' }
]

const generateAgentName = (sourceType, queryParams) => {
  if (sourceType === 'twitter') {
    const topic = queryParams.topic || 'Analysis'
    const handles = queryParams.handles || []
    if (handles.length > 0) {
      const handlesStr = handles.length === 1 
        ? handles[0].replace('@', '') 
        : `${handles[0].replace('@', '')} +${handles.length - 1}`
      return `Twitter: ${topic} (${handlesStr})`
    }
    return `Twitter: ${topic}`
  } else if (sourceType === 'reddit') {
    const subreddit = queryParams.subreddit || 'unknown'
    return `Reddit: r/${subreddit}`
  } else if (sourceType === 'polymarket') {
    const keyword = queryParams.keyword || 'Search'
    return `Polymarket: ${keyword}`
  }
  return 'Scheduled Agent'
}

export default function AgentScheduler({ sourceType, queryParams, onClose, onSuccess }) {
  const [name, setName] = useState('')
  const [schedule, setSchedule] = useState('daily')
  const [scheduleTime, setScheduleTime] = useState('09:00')
  const [dayOfWeek, setDayOfWeek] = useState('0')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // Auto-generate name when component mounts or sourceType/queryParams change
  useEffect(() => {
    const generatedName = generateAgentName(sourceType, queryParams)
    setName(generatedName)
  }, [sourceType, queryParams])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const scheduleTimeValue = schedule === 'daily' ? scheduleTime : dayOfWeek

      const response = await fetch(`${API_URL}/agents/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name,
          source_type: sourceType,
          query_params: queryParams,
          schedule,
          schedule_time: scheduleTimeValue
        })
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to create agent')
      }

      const result = await response.json()
      if (onSuccess) onSuccess(result)
      if (onClose) onClose()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.5)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000
    }}>
      <div style={{
        backgroundColor: 'var(--bg-primary)',
        borderRadius: '8px',
        padding: '2rem',
        width: '90%',
        maxWidth: '500px',
        boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
          <h2 style={{ margin: 0 }}>Schedule Agent</h2>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              padding: '0.5rem',
              display: 'flex',
              alignItems: 'center',
              color: 'var(--text-secondary)'
            }}
          >
            <X size={20} />
          </button>
        </div>

        {error && (
          <div style={{
            padding: '0.75rem',
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            borderRadius: '4px',
            color: '#ef4444',
            marginBottom: '1rem',
            fontSize: '0.875rem'
          }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-group" style={{ marginBottom: '1rem' }}>
            <label>Agent Name</label>
            <input
              type="text"
              className="form-input"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Daily Twitter Analysis"
              required
            />
          </div>

          <div className="form-group" style={{ marginBottom: '1rem' }}>
            <label>Schedule Type</label>
            <div style={{ display: 'flex', gap: '1rem', marginTop: '0.5rem' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                <input
                  type="radio"
                  name="schedule"
                  value="daily"
                  checked={schedule === 'daily'}
                  onChange={(e) => setSchedule(e.target.value)}
                />
                <span>Daily</span>
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                <input
                  type="radio"
                  name="schedule"
                  value="weekly"
                  checked={schedule === 'weekly'}
                  onChange={(e) => setSchedule(e.target.value)}
                />
                <span>Weekly</span>
              </label>
            </div>
          </div>

          {schedule === 'daily' ? (
            <div className="form-group" style={{ marginBottom: '1rem' }}>
              <label>Time</label>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Clock size={16} style={{ color: 'var(--text-muted)' }} />
                <input
                  type="time"
                  className="form-input"
                  value={scheduleTime}
                  onChange={(e) => setScheduleTime(e.target.value)}
                  required
                />
              </div>
            </div>
          ) : (
            <div className="form-group" style={{ marginBottom: '1rem' }}>
              <label>Day of Week</label>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Calendar size={16} style={{ color: 'var(--text-muted)' }} />
                <select
                  className="form-input"
                  value={dayOfWeek}
                  onChange={(e) => setDayOfWeek(e.target.value)}
                  required
                >
                  {DAYS_OF_WEEK.map(day => (
                    <option key={day.value} value={day.value}>{day.label}</option>
                  ))}
                </select>
              </div>
            </div>
          )}

          <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end', marginTop: '1.5rem' }}>
            <button
              type="button"
              onClick={onClose}
              style={{
                padding: '0.5rem 1rem',
                backgroundColor: 'var(--bg-secondary)',
                border: '1px solid var(--border-color)',
                borderRadius: '4px',
                color: 'var(--text-primary)',
                cursor: 'pointer'
              }}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="save-btn"
            >
              {loading ? 'Creating...' : 'Create Agent'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}


import { useState, useEffect } from 'react'
import { Calendar, Clock, Play, Pause, Trash2, RefreshCw, AlertCircle } from 'lucide-react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const DAYS_OF_WEEK = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

export default function AgentList({ onRunAgent }) {
  const [agents, setAgents] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadAgents = async () => {
    try {
      const response = await fetch(`${API_URL}/agents`)
      if (!response.ok) throw new Error('Failed to load agents')
      const data = await response.json()
      setAgents(data.agents || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadAgents()
    // Refresh every 30 seconds
    const interval = setInterval(loadAgents, 30000)
    return () => clearInterval(interval)
  }, [])

  const handleToggleStatus = async (agentId, currentStatus) => {
    const newStatus = currentStatus === 'active' ? 'paused' : 'active'
    
    try {
      const response = await fetch(`${API_URL}/agents/${agentId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus })
      })

      if (!response.ok) throw new Error('Failed to update agent')
      await loadAgents()
    } catch (err) {
      setError(err.message)
    }
  }

  const handleDelete = async (agentId) => {
    if (!confirm('Are you sure you want to delete this agent?')) return

    try {
      const response = await fetch(`${API_URL}/agents/${agentId}`, {
        method: 'DELETE'
      })

      if (!response.ok) throw new Error('Failed to delete agent')
      await loadAgents()
    } catch (err) {
      setError(err.message)
    }
  }

  const handleRunNow = async (agentId) => {
    try {
      // First, fetch the agent data
      const agentResponse = await fetch(`${API_URL}/agents/${agentId}`)
      if (!agentResponse.ok) throw new Error('Failed to fetch agent')
      const agent = await agentResponse.json()
      
      // If onRunAgent callback is provided, open a new tab
      if (onRunAgent) {
        const queryParams = agent.query_params || {}
        
        if (agent.source_type === 'twitter') {
          onRunAgent('twitter-results', `Twitter: ${queryParams.topic || 'Analysis'}`, {
            handles: queryParams.handles || [],
            topic: queryParams.topic || 'Analysis',
            timeframe: queryParams.timeframe || 1,
            processingMode: queryParams.processing_mode || 'batch',
            status: 'loading'
          })
        } else if (agent.source_type === 'reddit') {
          onRunAgent('reddit-results', `r/${queryParams.subreddit || 'unknown'}`, {
            subreddit: queryParams.subreddit || '',
            postCount: queryParams.post_count || 10,
            status: 'loading'
          })
        } else if (agent.source_type === 'polymarket') {
          // For Polymarket, we need to do a search first
          onRunAgent('polymarket-results', `PM: ${queryParams.keyword || 'Search'}`, {
            keyword: queryParams.keyword || '',
            results: null,
            status: 'loading'
          })
        }
      } else {
        // Fallback: trigger backend execution
        const response = await fetch(`${API_URL}/agents/${agentId}/run`, {
          method: 'POST'
        })

        if (!response.ok) throw new Error('Failed to run agent')
        alert('Agent execution started. Check backend logs for progress.')
      }
    } catch (err) {
      setError(err.message)
    }
  }

  const formatNextRun = (nextRun) => {
    if (!nextRun) return 'Not scheduled'
    try {
      const date = new Date(nextRun)
      // Format in Asia/Bangkok timezone (UTC+7)
      return date.toLocaleString('en-US', {
        timeZone: 'Asia/Bangkok',
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: true
      }) + ' (Bangkok)'
    } catch {
      return nextRun
    }
  }

  const formatSchedule = (agent) => {
    if (agent.schedule === 'daily') {
      return `Daily at ${agent.schedule_time} (Bangkok, UTC+7)`
    } else {
      const dayIndex = parseInt(agent.schedule_time)
      return `Weekly on ${DAYS_OF_WEEK[dayIndex]}`
    }
  }

  if (loading) {
    return (
      <div className="results-panel">
        <div style={{ textAlign: 'center', padding: '2rem' }}>
          <RefreshCw size={24} className="spinning" style={{ marginBottom: '1rem' }} />
          <p>Loading agents...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="results-panel">
      <div className="results-header">
        <div>
          <h3>Scheduled Agents</h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '0.25rem' }}>
            {agents.length} agent{agents.length !== 1 ? 's' : ''} configured
          </p>
        </div>
        <button
          className="save-btn"
          onClick={loadAgents}
          title="Refresh"
        >
          <RefreshCw size={16} />
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
          fontSize: '0.875rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem'
        }}>
          <AlertCircle size={16} />
          {error}
        </div>
      )}

      {agents.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
          <Calendar size={48} style={{ marginBottom: '1rem', opacity: 0.5 }} />
          <p>No scheduled agents yet.</p>
          <p style={{ fontSize: '0.875rem', marginTop: '0.5rem' }}>
            Create an agent from any analysis results page.
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {agents.map(agent => (
            <div
              key={agent.id}
              style={{
                padding: '1.5rem',
                backgroundColor: 'var(--bg-secondary)',
                borderRadius: '8px',
                border: `1px solid ${agent.status === 'active' ? 'rgba(34, 197, 94, 0.3)' : 'var(--border-color)'}`
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
                <div style={{ flex: 1 }}>
                  <h4 style={{ margin: '0 0 0.5rem 0' }}>{agent.name}</h4>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', fontSize: '0.875rem', color: 'var(--text-muted)' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                      <Calendar size={14} />
                      {formatSchedule(agent)}
                    </span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                      <Clock size={14} />
                      Next: {formatNextRun(agent.next_run)}
                    </span>
                    {agent.last_run && (
                      <span>
                        Last: {new Date(agent.last_run).toLocaleString('en-US', {
                          timeZone: 'Asia/Bangkok',
                          year: 'numeric',
                          month: '2-digit',
                          day: '2-digit',
                          hour: '2-digit',
                          minute: '2-digit',
                          second: '2-digit',
                          hour12: true
                        })} (Bangkok)
                      </span>
                    )}
                  </div>
                  <div style={{ marginTop: '0.5rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    Source: <strong>{agent.source_type}</strong>
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button
                    onClick={() => handleRunNow(agent.id)}
                    title="Run now"
                    style={{
                      padding: '0.5rem',
                      backgroundColor: 'var(--bg-primary)',
                      border: '1px solid var(--border-color)',
                      borderRadius: '4px',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      color: 'var(--text-primary)'
                    }}
                  >
                    <Play size={16} />
                  </button>
                  <button
                    onClick={() => handleToggleStatus(agent.id, agent.status)}
                    title={agent.status === 'active' ? 'Pause' : 'Resume'}
                    style={{
                      padding: '0.5rem',
                      backgroundColor: agent.status === 'active' ? 'rgba(239, 68, 68, 0.1)' : 'rgba(34, 197, 94, 0.1)',
                      border: `1px solid ${agent.status === 'active' ? 'rgba(239, 68, 68, 0.3)' : 'rgba(34, 197, 94, 0.3)'}`,
                      borderRadius: '4px',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      color: agent.status === 'active' ? '#ef4444' : '#22c55e'
                    }}
                  >
                    {agent.status === 'active' ? <Pause size={16} /> : <Play size={16} />}
                  </button>
                  <button
                    onClick={() => handleDelete(agent.id)}
                    title="Delete"
                    style={{
                      padding: '0.5rem',
                      backgroundColor: 'rgba(239, 68, 68, 0.1)',
                      border: '1px solid rgba(239, 68, 68, 0.3)',
                      borderRadius: '4px',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      color: '#ef4444'
                    }}
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
              <div style={{
                padding: '0.5rem',
                backgroundColor: agent.status === 'active' ? 'rgba(34, 197, 94, 0.1)' : 'rgba(107, 114, 128, 0.1)',
                borderRadius: '4px',
                fontSize: '0.75rem',
                color: agent.status === 'active' ? '#22c55e' : 'var(--text-muted)',
                display: 'inline-block'
              }}>
                {agent.status === 'active' ? 'Active' : 'Paused'}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}


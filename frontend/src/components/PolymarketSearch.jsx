import { useState, useEffect } from 'react'
import { Search, TrendingUp, DollarSign, BarChart3, Download, Check, AlertCircle } from 'lucide-react'
import { generatePolymarketResultsMarkdown, downloadMarkdown } from '../utils/exportMarkdown'
import { saveQueryToHistory } from './QueryHistory'

// Backend API URL
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const formatVolume = (volume) => {
  if (!volume) return '$0'
  const num = parseFloat(volume)
  if (num >= 1000000) {
    return `$${(num / 1000000).toFixed(1)}M`
  }
  if (num >= 1000) {
    return `$${(num / 1000).toFixed(0)}K`
  }
  return `$${num.toFixed(0)}`
}

export default function PolymarketSearch({ onSearch, initialKeyword, showResults, onMarketSelect }) {
  const [keyword, setKeyword] = useState(initialKeyword || '')
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [saved, setSaved] = useState(false)
  const [apiError, setApiError] = useState(null)

  useEffect(() => {
    if (showResults && initialKeyword) {
      fetchResults(initialKeyword)
    }
  }, [showResults, initialKeyword])

  const fetchResults = async (searchKeyword) => {
    setLoading(true)
    setApiError(null)
    
    try {
      const response = await fetch(
        `${API_URL}/polymarket/search?q=${encodeURIComponent(searchKeyword)}&limit=20`,
        { method: 'GET' }
      )
      
      if (!response.ok) {
        throw new Error(`API error: ${response.status} ${response.statusText}`)
      }
      
      const data = await response.json()
      
      // Transform events to match our display format
      const events = (data.events || []).map(event => ({
        id: event.id,
        slug: event.slug,
        title: event.title,
        description: event.description || '',
        volume: parseFloat(event.volume || 0),
        liquidity: parseFloat(event.liquidity || 0),
        url: `https://polymarket.com/event/${event.slug}`,
        markets: event.markets || [],
        closed: event.closed,
        endDate: event.endDate
      }))
      
      setResults(events)
      
      // Save to query history
      saveQueryToHistory('polymarket', { keyword: searchKeyword }, `Polymarket: ${searchKeyword}`)
    } catch (error) {
      console.error('Polymarket search error:', error)
      setApiError(error.message)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!keyword.trim()) return
    onSearch(keyword)
  }

  const handleSave = () => {
    const { content, filename } = generatePolymarketResultsMarkdown(initialKeyword, results)
    downloadMarkdown(content, filename)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner" />
        <div className="loading-text">Searching Polymarket for "{initialKeyword}"...</div>
      </div>
    )
  }

  if (apiError) {
    return (
      <div className="results-panel">
        <div style={{
          background: 'rgba(252, 92, 101, 0.1)',
          border: '1px solid var(--accent-red)',
          borderRadius: '12px',
          padding: '2rem',
          textAlign: 'center'
        }}>
          <AlertCircle size={48} style={{ color: 'var(--accent-red)', marginBottom: '1rem' }} />
          <h3 style={{ marginBottom: '0.5rem' }}>API Error</h3>
          <p style={{ color: 'var(--text-secondary)' }}>{apiError}</p>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '1rem' }}>
            Make sure the backend server is running at {API_URL}
          </p>
        </div>
      </div>
    )
  }

  if (showResults && results) {
    return (
      <div className="results-panel">
        <div className="results-header">
          <h3>Results for "{initialKeyword}"</h3>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <span className="results-count">{results.length} markets found</span>
            <button 
              className={`save-btn ${saved ? 'saved' : ''}`}
              onClick={handleSave}
              disabled={saved || results.length === 0}
            >
              {saved ? <Check size={16} /> : <Download size={16} />}
              {saved ? 'Saved!' : 'Save MD'}
            </button>
          </div>
        </div>

        {results.length === 0 && (
          <div style={{
            textAlign: 'center',
            padding: '3rem',
            color: 'var(--text-muted)'
          }}>
            <Search size={48} style={{ marginBottom: '1rem', opacity: 0.5 }} />
            <p>No markets found for "{initialKeyword}"</p>
          </div>
        )}

        {results.map((market, index) => (
          <div 
            key={market.id || index} 
            className="market-card"
            onClick={() => onMarketSelect(market)}
            style={{ animationDelay: `${index * 0.05}s` }}
          >
            <div className="market-card-header">
              <div className="market-title">{market.title}</div>
              <div className="market-volume">{formatVolume(market.volume)}</div>
            </div>
            <div className="market-description">
              {market.description ? market.description.slice(0, 150) + '...' : 'No description available'}
            </div>
            <div className="market-meta">
              <span>
                <DollarSign size={14} />
                Liquidity: {formatVolume(market.liquidity)}
              </span>
              <span>
                <BarChart3 size={14} />
                Volume: {formatVolume(market.volume)}
              </span>
            </div>
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="input-panel">
      <div className="panel-header">
        <div className="panel-icon polymarket">
          <TrendingUp color="white" size={24} />
        </div>
        <div>
          <h2>Polymarket Search</h2>
          <p>Search for prediction markets by keyword</p>
        </div>
      </div>

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label>Search Keywords</label>
          <input
            type="text"
            className="form-input"
            placeholder="e.g., AI, Bitcoin, Election, S&P 500..."
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
          />
        </div>

        <button type="submit" className="submit-btn purple">
          <Search size={18} />
          Search Markets
        </button>
      </form>
    </div>
  )
}

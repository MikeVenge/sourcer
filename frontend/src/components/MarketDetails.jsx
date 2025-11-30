import { useState, useEffect, useRef } from 'react'
import { TrendingUp, ExternalLink, Download, Check, AlertCircle, Calendar, DollarSign, RefreshCw } from 'lucide-react'
import { generateMarketDetailsMarkdown, downloadMarkdown } from '../utils/exportMarkdown'
import DistributionChart from './DistributionChart'
import PriceHistoryChart from './PriceHistoryChart'
import NotebookLMExport from './NotebookLMExport'

// Backend API URL
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const formatVolume = (volume) => {
  if (!volume) return '$0'
  const num = parseFloat(volume)
  if (num >= 1000000) {
    return `$${(num / 1000000).toFixed(1)}M`
  }
  if (num >= 1000) {
    return `$${Math.round(num / 1000).toLocaleString()}K`
  }
  return `$${Math.round(num).toLocaleString()}`
}

const formatVolumeSmall = (volume) => {
  if (!volume) return '$0 Vol.'
  const num = parseFloat(volume)
  if (num >= 1000000) {
    return `$${(num / 1000000).toFixed(1)}M Vol.`
  }
  if (num >= 1000) {
    return `$${Math.round(num / 1000).toLocaleString()},${Math.round(num % 1000).toString().padStart(3, '0').slice(0, 3)} Vol.`
  }
  return `$${Math.round(num).toLocaleString()} Vol.`
}

// Extract price from outcome name like "↑ $185", "↓ $160", "$200"
const extractPriceFromName = (name) => {
  const match = name.match(/\$?([\d,.]+)([KMBTkmbt])?/)
  if (!match) return 0
  let value = parseFloat(match[1].replace(/,/g, ''))
  const suffix = match[2]?.toUpperCase()
  if (suffix === 'K') value *= 1000
  if (suffix === 'M') value *= 1000000
  if (suffix === 'B') value *= 1000000000
  if (suffix === 'T') value *= 1000000000000
  return value
}

export default function MarketDetails({ data, tabId, updateTabData }) {
  // Check if we have saved details from previous session
  const hasSavedDetails = data?.details && data.details.outcomes
  
  const [loading, setLoading] = useState(false)
  const [details, setDetails] = useState(hasSavedDetails ? data.details : null)
  const [saved, setSaved] = useState(false)
  const [apiError, setApiError] = useState(null)
  const [refreshing, setRefreshing] = useState(false)
  const hasLoadedRef = useRef(hasSavedDetails) // Mark as loaded if we have saved details
  const slugRef = useRef(hasSavedDetails ? data.market.slug : '')

  const fetchDetails = async (isRefresh = false) => {
    setLoading(true)
    if (isRefresh) setRefreshing(true)
    setApiError(null)
    
    try {
      const slug = data.market.slug
      const response = await fetch(`${API_URL}/polymarket/event/${slug}`)
      
      if (!response.ok) {
        throw new Error(`API error: ${response.status} ${response.statusText}`)
      }
      
      const eventData = await response.json()
      
      // Parse outcomes from markets
      // Only include OPEN (not closed) markets
      const markets = eventData.markets || []
      const outcomes = []
      
      markets.forEach(market => {
        // Skip closed markets
        if (market.closed) return
        
        // Get the outcome name from groupItemTitle or question
        const name = market.groupItemTitle || market.question || 'Unknown'
        
        // Parse outcome prices - first price is "Yes" probability
        let outcomePrices = market.outcomePrices || '[]'
        if (typeof outcomePrices === 'string') {
          try { outcomePrices = JSON.parse(outcomePrices) } catch { outcomePrices = [] }
        }
        
        // The first price is the "Yes" probability (chance this outcome wins)
        const yesProbability = outcomePrices[0] ? parseFloat(outcomePrices[0]) : 0
        const noProbability = outcomePrices[1] ? parseFloat(outcomePrices[1]) : 1 - yesProbability
        
        outcomes.push({
          name: name,
          probability: yesProbability,
          yesPrice: Math.round(yesProbability * 100),
          noPrice: Math.round(noProbability * 100),
          volume: parseFloat(market.volume || 0),
          closed: market.closed
        })
      })
      
      // Sort outcomes by price descending (highest price first)
      // Filter out very low probability outcomes (< 0.5%)
      const filteredOutcomes = outcomes
        .filter(o => o.probability >= 0.005)
        .sort((a, b) => extractPriceFromName(b.name) - extractPriceFromName(a.name))
      
      const fetchedDetails = {
        ...data.market,
        title: eventData.title,
        description: eventData.description,
        volume: parseFloat(eventData.volume || 0),
        liquidity: parseFloat(eventData.liquidity || 0),
        endDate: eventData.endDate ? new Date(eventData.endDate).toLocaleDateString('en-US', { 
          month: 'short', 
          day: 'numeric', 
          year: 'numeric' 
        }) : 'N/A',
        outcomes: filteredOutcomes.length > 0 ? filteredOutcomes : null,
        url: `https://polymarket.com/event/${eventData.slug}`
      }
      
      setDetails(fetchedDetails)
      
      // Save details to tab data for persistence
      if (tabId && updateTabData) {
        updateTabData(tabId, {
          ...data,
          details: fetchedDetails
        })
      }
      
      hasLoadedRef.current = true
      slugRef.current = slug
    } catch (error) {
      console.error('Market details error:', error)
      setApiError(error.message)
      setDetails({
        ...data.market,
        outcomes: null
      })
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    // Only fetch if we haven't loaded yet OR if the slug has changed
    const currentSlug = data.market.slug
    if (!hasLoadedRef.current || slugRef.current !== currentSlug) {
      fetchDetails(false)
    }
  }, [data])

  const handleSave = () => {
    if (!details) return
    const { content, filename } = generateMarketDetailsMarkdown(details)
    downloadMarkdown(content, filename, 'polymarket-details', { 
      title: details.title,
      slug: details.slug 
    })
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner" />
        <div className="loading-text">Loading market details...</div>
      </div>
    )
  }

  if (apiError && !details) {
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
          <h3 style={{ marginBottom: '0.5rem' }}>Error Loading Market</h3>
          <p style={{ color: 'var(--text-secondary)' }}>{apiError}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="details-panel">
      {/* Header */}
      <div style={{ 
        background: 'var(--bg-card)', 
        border: '1px solid var(--border-color)',
        borderRadius: '16px',
        padding: '1.5rem',
        marginBottom: '1rem'
      }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <div className="panel-icon polymarket">
              <TrendingUp color="white" size={24} />
            </div>
            <div>
              <h1 style={{ 
                fontSize: '1.25rem', 
                fontWeight: 600, 
                marginBottom: '0.5rem',
                color: 'var(--text-primary)'
              }}>
                {details?.title || 'Loading...'}
              </h1>
              <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem', color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <DollarSign size={14} />
                  {formatVolume(details?.volume)} Vol.
                </span>
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <Calendar size={14} />
                  {details?.endDate}
                </span>
              </div>
            </div>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button 
              className="save-btn"
              onClick={() => fetchDetails(true)}
              disabled={refreshing}
              title="Refresh data"
            >
              <RefreshCw size={16} className={refreshing ? 'spinning' : ''} />
              {refreshing ? 'Refreshing...' : 'Refresh'}
            </button>
            <button 
              className={`save-btn ${saved ? 'saved' : ''}`}
              onClick={handleSave}
              disabled={saved || !details}
            >
              {saved ? <Check size={16} /> : <Download size={16} />}
              {saved ? 'Saved!' : 'Save MD'}
            </button>
            {details && (
              <NotebookLMExport 
                content={generateMarketDetailsMarkdown(details).content}
                sourceName={`Polymarket: ${details.title}`}
                sourceType="polymarket"
              />
            )}
            <a 
              href={details?.url}
              target="_blank"
              rel="noopener noreferrer"
              className="save-btn"
              style={{ textDecoration: 'none' }}
            >
              <ExternalLink size={16} />
              Polymarket
            </a>
          </div>
        </div>
      </div>

      {/* Distribution Chart */}
      {details?.outcomes && details.outcomes.length >= 3 && (
        <DistributionChart 
          outcomes={details.outcomes} 
          title="Price Probability Distribution"
        />
      )}

      {/* Price History Chart */}
      {data?.market?.slug && (
        <PriceHistoryChart 
          slug={data.market.slug} 
          title="Price History"
        />
      )}

      {/* Outcomes Table */}
      {details?.outcomes && details.outcomes.length > 0 && (
        <div style={{ 
          background: 'var(--bg-card)', 
          border: '1px solid var(--border-color)',
          borderRadius: '16px',
          overflow: 'hidden'
        }}>
          {/* Table Header */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr 120px 180px',
            padding: '1rem 1.5rem',
            borderBottom: '1px solid var(--border-color)',
            fontSize: '0.75rem',
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            color: 'var(--text-muted)'
          }}>
            <div>Outcome</div>
            <div style={{ textAlign: 'center' }}>% Chance</div>
            <div style={{ textAlign: 'center' }}>Price</div>
          </div>

          {/* Outcomes */}
          {details.outcomes.map((outcome, index) => (
            <div 
              key={index} 
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 120px 180px',
                padding: '1rem 1.5rem',
                borderBottom: index < details.outcomes.length - 1 ? '1px solid var(--border-color)' : 'none',
                alignItems: 'center',
                transition: 'background 0.2s',
              }}
              className="outcome-row"
            >
              {/* Outcome Name & Volume */}
              <div>
                <div style={{ fontWeight: 500, marginBottom: '0.25rem' }}>{outcome.name}</div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  {formatVolume(outcome.volume)} Vol.
                </div>
              </div>

              {/* Percentage */}
              <div style={{ 
                textAlign: 'center',
                fontSize: '1.5rem',
                fontWeight: 600,
                color: outcome.probability >= 0.5 ? 'var(--accent-green)' : 'var(--text-primary)'
              }}>
                {Math.round(outcome.probability * 100)}%
              </div>

              {/* Buy Yes/No Buttons */}
              <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'center' }}>
                <div style={{
                  padding: '0.5rem 0.75rem',
                  borderRadius: '6px',
                  background: 'rgba(38, 166, 91, 0.15)',
                  color: '#26a65b',
                  fontSize: '0.85rem',
                  fontWeight: 500,
                  minWidth: '70px',
                  textAlign: 'center'
                }}>
                  Yes {outcome.yesPrice}¢
                </div>
                <div style={{
                  padding: '0.5rem 0.75rem',
                  borderRadius: '6px',
                  background: 'rgba(252, 92, 101, 0.15)',
                  color: '#fc5c65',
                  fontSize: '0.85rem',
                  fontWeight: 500,
                  minWidth: '70px',
                  textAlign: 'center'
                }}>
                  No {outcome.noPrice}¢
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* No outcomes */}
      {(!details?.outcomes || details.outcomes.length === 0) && (
        <div style={{ 
          background: 'var(--bg-card)', 
          border: '1px solid var(--border-color)',
          borderRadius: '16px',
          padding: '3rem',
          textAlign: 'center'
        }}>
          <p style={{ color: 'var(--text-muted)', marginBottom: '1rem' }}>
            No open outcomes available for this market.
          </p>
          <a 
            href={details?.url}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.5rem',
              color: 'var(--accent-cyan)',
              textDecoration: 'none',
              fontSize: '0.9rem'
            }}
          >
            View on Polymarket <ExternalLink size={14} />
          </a>
        </div>
      )}

      {/* Description */}
      {details?.description && (
        <div style={{ 
          background: 'var(--bg-card)', 
          border: '1px solid var(--border-color)',
          borderRadius: '16px',
          padding: '1.5rem',
          marginTop: '1rem'
        }}>
          <h3 style={{ 
            fontSize: '0.85rem', 
            textTransform: 'uppercase', 
            letterSpacing: '0.05em',
            color: 'var(--text-muted)',
            marginBottom: '0.75rem'
          }}>
            Description
          </h3>
          <p style={{ 
            color: 'var(--text-secondary)', 
            lineHeight: 1.6,
            fontSize: '0.9rem'
          }}>
            {details.description}
          </p>
        </div>
      )}
    </div>
  )
}

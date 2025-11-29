import { useState, useEffect, useMemo } from 'react'
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip
} from 'recharts'
import { Activity } from 'lucide-react'

// Backend API URL
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Colors for top 3 outcomes - distinct and easy to differentiate
const OUTCOME_COLORS = [
  '#f97316',  // orange (1st)
  '#3b82f6',  // blue (2nd)
  '#22c55e',  // green (3rd)
]

/**
 * PriceHistoryChart - displays historical price data for all outcomes in a Polymarket market
 */
export default function PriceHistoryChart({ slug, title }) {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [priceData, setPriceData] = useState(null)
  const [timeRange, setTimeRange] = useState('all') // 'all', '30d', '7d', '24h'

  useEffect(() => {
    const fetchPriceHistory = async () => {
      if (!slug) return
      
      setLoading(true)
      setError(null)
      
      try {
        // Use hourly fidelity for more detail
        const response = await fetch(
          `${API_URL}/polymarket/price-history-all/${slug}?fidelity=60`
        )
        
        if (!response.ok) {
          throw new Error(`API error: ${response.status}`)
        }
        
        const data = await response.json()
        setPriceData(data)
      } catch (err) {
        console.error('Price history error:', err)
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }
    
    fetchPriceHistory()
  }, [slug])

  // Process and merge all market histories into a single dataset
  const { chartData, outcomes } = useMemo(() => {
    if (!priceData?.markets?.length) return { chartData: [], outcomes: [] }
    
    const now = Date.now() / 1000
    let cutoff = 0
    
    switch (timeRange) {
      case '24h':
        cutoff = now - 24 * 60 * 60
        break
      case '7d':
        cutoff = now - 7 * 24 * 60 * 60
        break
      case '30d':
        cutoff = now - 30 * 24 * 60 * 60
        break
      default:
        cutoff = 0
    }
    
    // Collect all unique timestamps
    const timestampSet = new Set()
    priceData.markets.forEach(market => {
      market.history?.forEach(h => {
        if (h.t >= cutoff) {
          timestampSet.add(h.t)
        }
      })
    })
    
    // Sort timestamps
    const timestamps = Array.from(timestampSet).sort((a, b) => a - b)
    
    // Build chart data with all outcomes
    const data = timestamps.map(t => {
      const point = { timestamp: t, date: new Date(t * 1000) }
      
      priceData.markets.forEach((market, idx) => {
        // Find the closest price point for this timestamp
        const historyPoint = market.history?.find(h => h.t === t)
        if (historyPoint) {
          // Use index as key to avoid special characters in keys
          point[`outcome_${idx}`] = historyPoint.p * 100
        }
      })
      
      return point
    })
    
    // Extract outcome info for legend
    const allOutcomes = priceData.markets.map((market, idx) => ({
      key: `outcome_${idx}`,
      name: market.name,
      currentProb: market.current_probability * 100
    }))
    
    // Sort by current probability, take top 3, and assign distinct colors
    const outcomes = [...allOutcomes]
      .sort((a, b) => b.currentProb - a.currentProb)
      .slice(0, 3)
      .map((outcome, idx) => ({
        ...outcome,
        color: OUTCOME_COLORS[idx]  // Orange for 1st, Blue for 2nd, Green for 3rd
      }))
    
    return { chartData: data, outcomes }
  }, [priceData, timeRange])

  const formatDate = (timestamp) => {
    const date = new Date(timestamp * 1000)
    if (timeRange === '24h') {
      return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
    }
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const date = new Date(label * 1000)
      return (
        <div style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--border-color)',
          borderRadius: '8px',
          padding: '0.75rem 1rem',
          boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
          minWidth: '150px'
        }}>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
            {date.toLocaleDateString('en-US', { 
              month: 'short', 
              day: 'numeric', 
              year: 'numeric',
              hour: '2-digit',
              minute: '2-digit'
            })}
          </p>
          {payload.map((entry, idx) => {
            const outcome = outcomes.find(o => o.key === entry.dataKey)
            return (
              <div key={idx} style={{ 
                display: 'flex', 
                justifyContent: 'space-between', 
                alignItems: 'center',
                gap: '1rem',
                marginBottom: '0.25rem'
              }}>
                <span style={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  gap: '0.5rem',
                  fontSize: '0.85rem',
                  color: 'var(--text-secondary)'
                }}>
                  <span style={{ 
                    width: '8px', 
                    height: '8px', 
                    borderRadius: '50%', 
                    background: entry.color 
                  }} />
                  {outcome?.name || entry.name}
                </span>
                <span style={{ 
                  fontWeight: 600, 
                  color: entry.color,
                  fontFamily: 'var(--font-mono)'
                }}>
                  {entry.value?.toFixed(1)}%
                </span>
              </div>
            )
          })}
        </div>
      )
    }
    return null
  }

  // Custom legend component
  const renderLegend = () => {
    return (
      <div style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: '0.75rem 1.5rem',
        marginBottom: '1rem',
        padding: '0.5rem 0'
      }}>
        {outcomes.map((outcome, idx) => (
          <div key={idx} style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '0.5rem',
            fontSize: '0.85rem'
          }}>
            <span style={{ 
              width: '10px', 
              height: '10px', 
              borderRadius: '50%', 
              background: outcome.color,
              flexShrink: 0
            }} />
            <span style={{ color: 'var(--text-secondary)' }}>
              {outcome.name}
            </span>
            <span style={{ 
              fontWeight: 600, 
              color: outcome.color,
              fontFamily: 'var(--font-mono)'
            }}>
              {outcome.currentProb.toFixed(0)}%
            </span>
          </div>
        ))}
      </div>
    )
  }

  if (loading) {
    return (
      <div style={{ 
        background: 'var(--bg-card)', 
        border: '1px solid var(--border-color)',
        borderRadius: '16px',
        padding: '2rem',
        textAlign: 'center'
      }}>
        <Activity size={32} style={{ color: 'var(--text-muted)', marginBottom: '0.5rem' }} />
        <p style={{ color: 'var(--text-muted)' }}>Loading price history...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div style={{ 
        background: 'var(--bg-card)', 
        border: '1px solid var(--border-color)',
        borderRadius: '16px',
        padding: '2rem',
        textAlign: 'center'
      }}>
        <p style={{ color: 'var(--accent-red)' }}>Unable to load price history</p>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>{error}</p>
      </div>
    )
  }

  if (!chartData.length) {
    return null
  }

  return (
    <div style={{ 
      background: 'var(--bg-card)', 
      border: '1px solid var(--border-color)',
      borderRadius: '16px',
      padding: '1.5rem',
      marginTop: '1rem'
    }}>
      {/* Header */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'flex-start',
        marginBottom: '0.5rem',
        flexWrap: 'wrap',
        gap: '1rem'
      }}>
        <h3 style={{ 
          fontSize: '0.85rem', 
          textTransform: 'uppercase', 
          letterSpacing: '0.05em',
          color: 'var(--text-muted)'
        }}>
          Price History
        </h3>
        
        {/* Time Range Selector */}
        <div style={{ display: 'flex', gap: '0.25rem' }}>
          {[
            { key: 'all', label: 'All' },
            { key: '30d', label: '30D' },
            { key: '7d', label: '7D' },
            { key: '24h', label: '24H' }
          ].map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setTimeRange(key)}
              style={{
                padding: '0.4rem 0.75rem',
                border: 'none',
                borderRadius: '6px',
                fontSize: '0.8rem',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all 0.15s',
                background: timeRange === key 
                  ? 'linear-gradient(135deg, #8b5cf6, #6d28d9)' 
                  : 'var(--bg-tertiary)',
                color: timeRange === key ? 'white' : 'var(--text-secondary)'
              }}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Legend */}
      {renderLegend()}

      {/* Chart */}
      <div style={{ width: '100%', overflowX: 'auto' }}>
        <LineChart 
          width={850} 
          height={300} 
          data={chartData} 
          margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
          <XAxis 
            dataKey="timestamp"
            tickFormatter={formatDate}
            stroke="#9ca3af"
            fontSize={11}
            tickLine={false}
            axisLine={{ stroke: '#374151' }}
            interval="preserveStartEnd"
            minTickGap={50}
          />
          <YAxis 
            tickFormatter={(v) => `${v.toFixed(0)}%`}
            stroke="#9ca3af"
            fontSize={11}
            tickLine={false}
            axisLine={{ stroke: '#374151' }}
            domain={[0, 'auto']}
            width={45}
          />
          <Tooltip content={<CustomTooltip />} />
          {outcomes.map((outcome) => (
            <Line 
              key={outcome.key}
              type="stepAfter"
              dataKey={outcome.key}
              name={outcome.name}
              stroke={outcome.color}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: outcome.color, stroke: 'white', strokeWidth: 2 }}
              connectNulls
            />
          ))}
        </LineChart>
      </div>

      <p style={{ 
        fontSize: '0.75rem', 
        color: 'var(--text-muted)', 
        marginTop: '0.75rem',
        textAlign: 'center'
      }}>
        Top 3 outcomes • Hourly price data
      </p>
    </div>
  )
}

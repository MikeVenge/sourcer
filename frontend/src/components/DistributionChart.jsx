import { useMemo, useState } from 'react'
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ReferenceLine
} from 'recharts'

/**
 * Parse price levels from outcome names like "↑ $185", "↓ $160", "$200", etc.
 */
function parsePriceFromOutcome(name) {
  // Match patterns like "$185", "↑ $185", "↓ $160", "$1.5T", etc.
  const match = name.match(/\$?([\d,.]+)([KMBTkmbt])?/)
  if (!match) return null
  
  let value = parseFloat(match[1].replace(/,/g, ''))
  const suffix = match[2]?.toUpperCase()
  
  if (suffix === 'K') value *= 1000
  if (suffix === 'M') value *= 1000000
  if (suffix === 'B') value *= 1000000000
  if (suffix === 'T') value *= 1000000000000
  
  return value
}

/**
 * Build interpolated curve from discrete points
 */
function buildInterpolatedCurve(pairs, nPoints = 100) {
  if (pairs.length < 2) return pairs

  const prices = pairs.map(p => p.price)
  const probs = pairs.map(p => p.prob)
  
  const minPrice = Math.min(...prices)
  const maxPrice = Math.max(...prices)
  const range = maxPrice - minPrice
  const step = range / (nPoints - 1)
  
  const result = []
  for (let i = 0; i < nPoints; i++) {
    const x = minPrice + i * step
    // Linear interpolation
    let y = 0
    for (let j = 0; j < prices.length - 1; j++) {
      if (x >= prices[j] && x <= prices[j + 1]) {
        const t = (x - prices[j]) / (prices[j + 1] - prices[j])
        y = probs[j] + t * (probs[j + 1] - probs[j])
        break
      }
    }
    // Handle edges
    if (x <= prices[0]) y = probs[0]
    if (x >= prices[prices.length - 1]) y = probs[probs.length - 1]
    
    result.push({ price: x, probability: y * 100 }) // Convert to percentage
  }
  
  return result
}

/**
 * Calculate probability for a given price from the distribution curve
 */
function getProbabilityAtPrice(curve, targetPrice) {
  if (!curve || curve.length < 2) return null
  
  const minPrice = curve[0].price
  const maxPrice = curve[curve.length - 1].price
  
  // Check if price is in range
  if (targetPrice < minPrice || targetPrice > maxPrice) {
    return { probability: 0, outOfRange: true, minPrice, maxPrice }
  }
  
  // Find the two points surrounding the target price and interpolate
  for (let i = 0; i < curve.length - 1; i++) {
    if (targetPrice >= curve[i].price && targetPrice <= curve[i + 1].price) {
      const t = (targetPrice - curve[i].price) / (curve[i + 1].price - curve[i].price)
      const probability = curve[i].probability + t * (curve[i + 1].probability - curve[i].probability)
      return { probability, outOfRange: false }
    }
  }
  
  return { probability: 0, outOfRange: true, minPrice, maxPrice }
}

/**
 * DistributionChart component - displays probability distribution of market outcomes
 */
export default function DistributionChart({ outcomes, title }) {
  const [inputPrice, setInputPrice] = useState('')
  const [lookupResult, setLookupResult] = useState(null)
  
  const chartData = useMemo(() => {
    if (!outcomes || outcomes.length < 2) return null

    // Parse price levels and probabilities from outcomes
    const parsed = outcomes
      .map(o => ({
        price: parsePriceFromOutcome(o.name),
        prob: o.probability,
        name: o.name
      }))
      .filter(o => o.price !== null)
      .sort((a, b) => a.price - b.price)

    if (parsed.length < 2) return null

    // Build interpolated curve
    const interpolated = buildInterpolatedCurve(parsed, 100)

    // Find the peak (highest probability)
    const peakPrice = parsed.reduce((max, curr) => 
      curr.prob > max.prob ? curr : max, parsed[0]).price

    return { curve: interpolated, peak: peakPrice, rawPoints: parsed }
  }, [outcomes])

  // Handle price lookup
  const handleLookup = () => {
    if (!inputPrice || !chartData) return
    
    // Parse the input - handle formats like "185", "$185", "185.50"
    const cleanInput = inputPrice.replace(/[$,]/g, '')
    const targetPrice = parseFloat(cleanInput)
    
    if (isNaN(targetPrice)) {
      setLookupResult({ error: 'Please enter a valid number' })
      return
    }
    
    const result = getProbabilityAtPrice(chartData.curve, targetPrice)
    setLookupResult({ ...result, price: targetPrice })
  }

  // Handle enter key
  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleLookup()
    }
  }

  if (!chartData) {
    return null
  }

  const formatPrice = (value) => {
    if (value >= 1000000000000) return `$${(value / 1000000000000).toFixed(1)}T`
    if (value >= 1000000000) return `$${(value / 1000000000).toFixed(1)}B`
    if (value >= 1000000) return `$${(value / 1000000).toFixed(1)}M`
    if (value >= 1000) return `$${(value / 1000).toFixed(0)}K`
    return `$${value.toFixed(0)}`
  }

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      return (
        <div style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--border-color)',
          borderRadius: '8px',
          padding: '0.75rem 1rem',
          boxShadow: '0 4px 12px rgba(0,0,0,0.3)'
        }}>
          <p style={{ fontWeight: 600, marginBottom: '0.25rem' }}>
            {formatPrice(payload[0].payload.price)}
          </p>
          <p style={{ color: '#8b5cf6', fontSize: '0.9rem' }}>
            {payload[0].value.toFixed(1)}% probability
          </p>
        </div>
      )
    }
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
      <h3 style={{ 
        fontSize: '0.85rem', 
        textTransform: 'uppercase', 
        letterSpacing: '0.05em',
        color: 'var(--text-muted)',
        marginBottom: '1rem'
      }}>
        {title || 'Probability Distribution'}
      </h3>

      {/* Price Lookup Input */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.75rem',
        marginBottom: '1.5rem',
        padding: '1rem',
        background: 'rgba(139, 92, 246, 0.1)',
        borderRadius: '12px',
        border: '1px solid rgba(139, 92, 246, 0.2)'
      }}>
        <label style={{ 
          fontSize: '0.9rem', 
          color: 'var(--text-secondary)',
          whiteSpace: 'nowrap'
        }}>
          Price Level:
        </label>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flex: 1 }}>
          <span style={{ color: 'var(--text-muted)' }}>$</span>
          <input
            type="text"
            value={inputPrice}
            onChange={(e) => setInputPrice(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Enter price (e.g. 185)"
            style={{
              flex: 1,
              padding: '0.6rem 0.75rem',
              background: 'var(--bg-primary)',
              border: '1px solid var(--border-color)',
              borderRadius: '8px',
              color: 'var(--text-primary)',
              fontSize: '1rem',
              outline: 'none',
              minWidth: '120px'
            }}
          />
          <button
            onClick={handleLookup}
            style={{
              padding: '0.6rem 1.25rem',
              background: 'linear-gradient(135deg, #8b5cf6, #6d28d9)',
              border: 'none',
              borderRadius: '8px',
              color: 'white',
              fontSize: '0.9rem',
              fontWeight: 600,
              cursor: 'pointer',
              whiteSpace: 'nowrap',
              transition: 'transform 0.15s, box-shadow 0.15s'
            }}
            onMouseOver={(e) => {
              e.target.style.transform = 'translateY(-1px)'
              e.target.style.boxShadow = '0 4px 12px rgba(139, 92, 246, 0.4)'
            }}
            onMouseOut={(e) => {
              e.target.style.transform = 'translateY(0)'
              e.target.style.boxShadow = 'none'
            }}
          >
            Calculate
          </button>
        </div>

        {/* Result Display */}
        {lookupResult && (
          <div style={{
            padding: '0.5rem 1rem',
            background: lookupResult.error || lookupResult.outOfRange 
              ? 'rgba(239, 68, 68, 0.15)' 
              : 'rgba(34, 197, 94, 0.15)',
            borderRadius: '8px',
            border: `1px solid ${lookupResult.error || lookupResult.outOfRange 
              ? 'rgba(239, 68, 68, 0.3)' 
              : 'rgba(34, 197, 94, 0.3)'}`,
            minWidth: '150px',
            textAlign: 'center'
          }}>
            {lookupResult.error ? (
              <span style={{ color: '#ef4444', fontSize: '0.9rem' }}>{lookupResult.error}</span>
            ) : lookupResult.outOfRange ? (
              <span style={{ color: '#ef4444', fontSize: '0.85rem' }}>
                Out of range (${formatPrice(lookupResult.minPrice).replace('$','')} - ${formatPrice(lookupResult.maxPrice).replace('$','')})
              </span>
            ) : (
              <div>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Probability at ${lookupResult.price}</span>
                <div style={{ 
                  color: '#22c55e', 
                  fontSize: '1.5rem', 
                  fontWeight: 700,
                  fontFamily: 'var(--font-mono)'
                }}>
                  {lookupResult.probability.toFixed(1)}%
                </div>
              </div>
            )}
          </div>
        )}
      </div>
      
      <div style={{ width: '100%', overflowX: 'auto' }}>
        <AreaChart 
          width={800} 
          height={300} 
          data={chartData.curve} 
          margin={{ top: 10, right: 30, left: 10, bottom: 10 }}
        >
          <defs>
            <linearGradient id="probabilityGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.4}/>
              <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0.05}/>
            </linearGradient>
          </defs>
          <CartesianGrid 
            strokeDasharray="3 3" 
            stroke="#374151" 
            opacity={0.5}
          />
          <XAxis 
            dataKey="price" 
            tickFormatter={formatPrice}
            stroke="#9ca3af"
            fontSize={12}
            tickLine={false}
            axisLine={{ stroke: '#374151' }}
          />
          <YAxis 
            tickFormatter={(v) => `${v.toFixed(0)}%`}
            stroke="#9ca3af"
            fontSize={12}
            tickLine={false}
            axisLine={{ stroke: '#374151' }}
            domain={[0, 'auto']}
          />
          <Tooltip content={<CustomTooltip />} />
          <ReferenceLine 
            x={chartData.peak} 
            stroke="#00d4ff" 
            strokeDasharray="5 5"
            strokeWidth={2}
            label={{ value: 'Peak', position: 'top', fill: '#00d4ff', fontSize: 12 }}
          />
          <Area 
            type="monotone" 
            dataKey="probability" 
            stroke="#8b5cf6" 
            strokeWidth={2}
            fill="url(#probabilityGradient)"
            isAnimationActive={true}
            animationDuration={1000}
          />
        </AreaChart>
      </div>
      
      <p style={{ 
        fontSize: '0.8rem', 
        color: 'var(--text-muted)', 
        marginTop: '0.75rem',
        textAlign: 'center'
      }}>
        Interpolated probability distribution based on market prices
      </p>
    </div>
  )
}

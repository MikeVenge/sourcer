import { MessageCircle, TrendingUp, Youtube, MessageSquare, Calendar } from 'lucide-react'

export default function SourceSelector({ onSelect }) {
  return (
    <div className="source-selector compact">
      <h1>
        Choose Your <span>Data Source</span>
      </h1>
      
      <div className="source-cards-compact">
        <div 
          className="source-card-compact twitter"
          onClick={() => onSelect('twitter')}
        >
          <div className="source-icon">
            <MessageCircle color="white" size={32} />
          </div>
          <span>Twitter / X</span>
        </div>

        <div 
          className="source-card-compact polymarket"
          onClick={() => onSelect('polymarket')}
        >
          <div className="source-icon">
            <TrendingUp color="white" size={32} />
          </div>
          <span>Polymarket</span>
        </div>

        <div 
          className="source-card-compact youtube"
          onClick={() => onSelect('youtube')}
        >
          <div className="source-icon">
            <Youtube color="white" size={32} />
          </div>
          <span>YouTube</span>
        </div>

        <div 
          className="source-card-compact reddit"
          onClick={() => onSelect('reddit')}
        >
          <div className="source-icon">
            <MessageSquare color="white" size={32} />
          </div>
          <span>Reddit</span>
        </div>

        <div 
          className="source-card-compact"
          onClick={() => onSelect('agents')}
          style={{ 
            background: 'linear-gradient(135deg, rgba(139, 92, 246, 0.1) 0%, rgba(59, 130, 246, 0.1) 100%)',
            border: '1px solid rgba(139, 92, 246, 0.3)'
          }}
        >
          <div className="source-icon" style={{ background: 'linear-gradient(135deg, #8b5cf6 0%, #3b82f6 100%)' }}>
            <Calendar color="white" size={32} />
          </div>
          <span>Scheduled Agents</span>
        </div>
      </div>
    </div>
  )
}

import { MessageCircle, TrendingUp, Youtube, MessageSquare } from 'lucide-react'

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
      </div>
    </div>
  )
}

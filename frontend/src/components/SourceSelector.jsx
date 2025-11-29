import { MessageCircle, TrendingUp } from 'lucide-react'

export default function SourceSelector({ onSelect }) {
  return (
    <div className="source-selector">
      <h1>
        Choose Your <span>Data Source</span>
      </h1>
      
      <div className="source-cards">
        <div 
          className="source-card twitter"
          onClick={() => onSelect('twitter')}
        >
          <div className="source-icon">
            <MessageCircle color="white" size={36} />
          </div>
          <h2>Twitter / X</h2>
          <p>
            Analyze tweets from specific accounts. 
            Search for topics, trends, and insights 
            from thought leaders and influencers.
          </p>
        </div>

        <div 
          className="source-card polymarket"
          onClick={() => onSelect('polymarket')}
        >
          <div className="source-icon">
            <TrendingUp color="white" size={36} />
          </div>
          <h2>Polymarket</h2>
          <p>
            Search prediction markets by keyword. 
            Get real-time odds, trading volume, 
            and market sentiment data.
          </p>
        </div>
      </div>
    </div>
  )
}


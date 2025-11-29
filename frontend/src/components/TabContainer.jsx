import { X, Plus, Home, Search, MessageCircle, TrendingUp, Trash2 } from 'lucide-react'

const getTabIcon = (type) => {
  switch (type) {
    case 'home':
      return <Home size={14} />
    case 'twitter-input':
    case 'twitter-results':
      return <MessageCircle size={14} />
    case 'polymarket-search':
    case 'polymarket-results':
      return <Search size={14} />
    case 'market-details':
      return <TrendingUp size={14} />
    default:
      return null
  }
}

export default function TabContainer({ tabs, activeTabId, onTabClick, onTabClose, onAddTab, onClearAll }) {
  return (
    <div className="tab-container">
      {tabs.map((tab) => (
        <div
          key={tab.id}
          className={`tab ${tab.id === activeTabId ? 'active' : ''}`}
          onClick={() => onTabClick(tab.id)}
        >
          {getTabIcon(tab.type)}
          <span className="tab-title">{tab.title}</span>
          {tabs.length > 1 && (
            <button
              className="tab-close"
              onClick={(e) => {
                e.stopPropagation()
                onTabClose(tab.id)
              }}
            >
              <X size={12} />
            </button>
          )}
        </div>
      ))}
      <button className="tab-add" onClick={onAddTab} title="New Tab">
        <Plus size={16} />
      </button>
      {tabs.length > 1 && (
        <button 
          className="tab-clear" 
          onClick={() => {
            if (confirm('Clear all tabs and start fresh?')) {
              onClearAll()
            }
          }}
          title="Clear all tabs"
        >
          <Trash2 size={14} />
        </button>
      )}
    </div>
  )
}

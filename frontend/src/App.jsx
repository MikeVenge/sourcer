import { useState, useEffect } from 'react'
import './App.css'
import TabContainer from './components/TabContainer'
import SourceSelector from './components/SourceSelector'
import TwitterInput from './components/TwitterInput'
import PolymarketSearch from './components/PolymarketSearch'
import MarketDetails from './components/MarketDetails'
import TwitterResults from './components/TwitterResults'
import QueryHistory from './components/QueryHistory'
import SavedFiles from './components/SavedFiles'
import YouTubeInput from './components/YouTubeInput'
import YouTubeResults from './components/YouTubeResults'
import RedditInput from './components/RedditInput'
import RedditResults from './components/RedditResults'

// LocalStorage key for persisting tabs
const STORAGE_KEY = 'sourcer_tabs'

// Load tabs from localStorage
const loadTabsFromStorage = () => {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      const parsed = JSON.parse(saved)
      if (parsed.tabs && parsed.tabs.length > 0) {
        return {
          tabs: parsed.tabs,
          activeTabId: parsed.activeTabId || parsed.tabs[0].id,
          tabCounter: parsed.tabCounter || Math.max(...parsed.tabs.map(t => t.id)) + 1
        }
      }
    }
  } catch (e) {
    console.warn('Failed to load tabs from storage:', e)
  }
  // Default state
  return {
    tabs: [{ id: 1, type: 'home', title: 'Home', data: null }],
    activeTabId: 1,
    tabCounter: 2
  }
}

// Save tabs to localStorage
const saveTabsToStorage = (tabs, activeTabId, tabCounter) => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      tabs,
      activeTabId,
      tabCounter,
      savedAt: new Date().toISOString()
    }))
  } catch (e) {
    console.warn('Failed to save tabs to storage:', e)
  }
}

function App() {
  // Initialize state from localStorage
  const [initialized, setInitialized] = useState(false)
  const [tabs, setTabs] = useState([{ id: 1, type: 'home', title: 'Home', data: null }])
  const [activeTabId, setActiveTabId] = useState(1)
  const [tabCounter, setTabCounter] = useState(2)

  // Load from localStorage on mount
  useEffect(() => {
    const saved = loadTabsFromStorage()
    setTabs(saved.tabs)
    setActiveTabId(saved.activeTabId)
    setTabCounter(saved.tabCounter)
    setInitialized(true)
  }, [])

  // Save to localStorage whenever tabs change (after initial load)
  useEffect(() => {
    if (initialized) {
      saveTabsToStorage(tabs, activeTabId, tabCounter)
    }
  }, [tabs, activeTabId, tabCounter, initialized])

  const activeTab = tabs.find(t => t.id === activeTabId)

  const addTab = (type, title, data = null) => {
    const newTab = {
      id: tabCounter,
      type,
      title,
      data
    }
    setTabs([...tabs, newTab])
    setActiveTabId(tabCounter)
    setTabCounter(tabCounter + 1)
  }

  const closeTab = (tabId) => {
    if (tabs.length === 1) return
    const newTabs = tabs.filter(t => t.id !== tabId)
    if (activeTabId === tabId) {
      setActiveTabId(newTabs[newTabs.length - 1].id)
    }
    setTabs(newTabs)
  }

  const updateTabData = (tabId, data) => {
    setTabs(tabs.map(t => t.id === tabId ? { ...t, data } : t))
  }

  const clearAllTabs = () => {
    const defaultTabs = [{ id: 1, type: 'home', title: 'Home', data: null }]
    setTabs(defaultTabs)
    setActiveTabId(1)
    setTabCounter(2)
    localStorage.removeItem(STORAGE_KEY)
  }

  const handleSourceSelect = (source) => {
    if (source === 'twitter') {
      addTab('twitter-input', 'Twitter Analysis')
    } else if (source === 'polymarket') {
      addTab('polymarket-search', 'Polymarket Search')
    } else if (source === 'youtube') {
      addTab('youtube-input', 'YouTube Transcript')
    } else if (source === 'reddit') {
      addTab('reddit-input', 'Reddit Analysis')
    }
  }

  const handleRedditSubmit = (subreddit, postCount) => {
    addTab('reddit-results', `r/${subreddit}`, { subreddit, postCount, status: 'loading' })
  }

  const handleYouTubeSubmit = (url) => {
    // Extract video ID for tab title
    const match = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)/)
    const videoId = match ? match[1] : 'video'
    addTab('youtube-results', `YT: ${videoId}`, { url, status: 'loading' })
  }

  const handleTwitterSubmit = (handles, topic, timeframe) => {
    addTab('twitter-results', `Twitter: ${topic.slice(0, 20)}...`, { handles, topic, timeframe, status: 'loading' })
  }

  const handlePolymarketSearch = (keyword) => {
    addTab('polymarket-results', `PM: ${keyword}`, { keyword, results: null, status: 'loading' })
  }

  const handleMarketSelect = (market) => {
    addTab('market-details', market.title.slice(0, 25) + '...', { market, status: 'loading' })
  }

  // Handle re-running a query from history
  const handleHistorySelect = (historyItem) => {
    if (historyItem.type === 'polymarket') {
      // Re-run Polymarket search
      addTab('polymarket-results', `PM: ${historyItem.query.keyword}`, { 
        keyword: historyItem.query.keyword, 
        results: null, 
        status: 'loading' 
      })
    } else if (historyItem.type === 'twitter') {
      // Re-run Twitter analysis
      const topic = historyItem.query.topic || 'Analysis'
      addTab('twitter-results', `Twitter: ${topic.slice(0, 20)}...`, { 
        handles: historyItem.query.handles,
        topic: historyItem.query.topic,
        timeframe: historyItem.query.timeframe || 5,
        status: 'loading' 
      })
    } else if (historyItem.type === 'youtube') {
      // Re-run YouTube transcript
      const url = historyItem.query.url
      const match = url?.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)/)
      const videoId = match ? match[1] : 'video'
      addTab('youtube-results', `YT: ${videoId}`, { 
        url: historyItem.query.url,
        status: 'loading' 
      })
    } else if (historyItem.type === 'reddit') {
      // Re-run Reddit analysis
      addTab('reddit-results', `r/${historyItem.query.subreddit}`, { 
        subreddit: historyItem.query.subreddit,
        postCount: historyItem.query.postCount || 10,
        status: 'loading' 
      })
    }
  }

  const renderTabContent = () => {
    if (!activeTab) return null

    switch (activeTab.type) {
      case 'home':
        return (
          <div className="home-container">
            <SourceSelector onSelect={handleSourceSelect} />
            <QueryHistory onSelectQuery={handleHistorySelect} />
            <SavedFiles />
          </div>
        )
      case 'twitter-input':
        return <TwitterInput onSubmit={handleTwitterSubmit} />
      case 'twitter-results':
        return <TwitterResults data={activeTab.data} tabId={activeTab.id} updateTabData={updateTabData} />
      case 'youtube-input':
        return <YouTubeInput onSubmit={handleYouTubeSubmit} />
      case 'youtube-results':
        return <YouTubeResults data={activeTab.data} />
      case 'reddit-input':
        return <RedditInput onSubmit={handleRedditSubmit} />
      case 'reddit-results':
        return <RedditResults data={activeTab.data} tabId={activeTab.id} updateTabData={updateTabData} />
      case 'polymarket-search':
        return <PolymarketSearch onSearch={handlePolymarketSearch} />
      case 'polymarket-results':
        return (
          <PolymarketSearch 
            onSearch={handlePolymarketSearch} 
            initialKeyword={activeTab.data?.keyword}
            showResults={true}
            onMarketSelect={handleMarketSelect}
            tabId={activeTab.id}
            updateTabData={updateTabData}
            savedResults={activeTab.data?.results}
          />
        )
      case 'market-details':
        return <MarketDetails data={activeTab.data} tabId={activeTab.id} updateTabData={updateTabData} />
      default:
        return <div>Unknown tab type</div>
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="logo">
          <span className="logo-icon">◈</span>
          <span className="logo-text">Sourcer</span>
        </div>
        <div className="header-subtitle">Market Intelligence Platform</div>
      </header>
      
      <TabContainer 
        tabs={tabs}
        activeTabId={activeTabId}
        onTabClick={setActiveTabId}
        onTabClose={closeTab}
        onAddTab={() => addTab('home', 'New Tab')}
        onClearAll={clearAllTabs}
      />
      
      <main className="main-content">
        {renderTabContent()}
      </main>
    </div>
  )
}

export default App

// Utility functions for exporting results to markdown
// Format matches the Python twitter_reader_batch.py output

// Helper to generate consistent timestamp for filenames
const getTimestamp = () => {
  const now = new Date()
  const date = now.toISOString().split('T')[0].replace(/-/g, '')
  const time = now.toTimeString().split(' ')[0].replace(/:/g, '')
  return `${date}_${time}`
}

export const generateTwitterMarkdown = (data, posts) => {
  const timestamp = getTimestamp()
  const timeframe = data.timeframe || 5
  
  // Sort posts by views (descending) like twitter_reader_batch.py
  const sortedPosts = [...posts].sort((a, b) => (b.views || 0) - (a.views || 0))
  
  // Calculate summary stats
  const totalPosts = posts.length
  const uniqueAuthors = [...new Set(posts.map(p => p.author))].length
  const handlesWithPosts = uniqueAuthors
  const handlesWithNoPosts = data.handles.length - uniqueAuthors
  
  let md = `# Consolidated Twitter/X Analysis Report\n\n`
  md += `**Generated:** ${new Date().toISOString()}\n\n`
  md += `**Topic:** ${data.topic}\n\n`
  md += `**Timeframe:** ${timeframe} days\n\n`
  md += `**Accounts Analyzed:** ${data.handles.length}\n\n`
  md += `---\n\n`
  
  // Summary section (like twitter_reader_batch.py)
  md += `## Summary\n\n`
  md += `- **Total Posts Found:** ${totalPosts}\n`
  md += `- **Accounts with Relevant Posts:** ${handlesWithPosts}\n`
  md += `- **Accounts with No Posts:** ${handlesWithNoPosts}\n\n`
  md += `---\n\n`
  
  // All posts sorted by views (like twitter_reader_batch.py)
  md += `## All Posts (Sorted by Views)\n\n`

  sortedPosts.forEach((post, index) => {
    md += `### ${index + 1}. ${post.author_name || 'Unknown'} (@${post.author || 'unknown'})\n\n`
    md += `**URL:** ${post.url || 'N/A'}\n\n`
    
    if (post.text) {
      md += `**Content:**\n> ${post.text.replace(/\n/g, '\n> ')}\n\n`
    }
    
    // Stats (matching twitter_reader_batch.py format)
    const stats = []
    if (post.views) stats.push(`${post.views.toLocaleString()} views`)
    if (post.likes) stats.push(`${post.likes.toLocaleString()} likes`)
    if (post.retweets) stats.push(`${post.retweets.toLocaleString()} retweets`)
    if (post.replies) stats.push(`${post.replies.toLocaleString()} replies`)
    
    if (stats.length > 0) {
      md += `**Stats:** ${stats.join(' | ')}\n\n`
    }
    
    if (post.created_at) {
      md += `**Posted:** ${post.created_at}\n\n`
    }
    
    // Quoted tweet (like twitter_reader_batch.py)
    if (post.quoted_tweet) {
      const qt = post.quoted_tweet
      const qtAuthor = qt.author || {}
      md += `**Quoted Tweet from @${qtAuthor.screen_name || 'unknown'}:**\n`
      md += `> ${(qt.text || '').slice(0, 300)}...\n\n`
    }
    
    md += `---\n\n`
  })
  
  // Results by account (like twitter_reader_batch.py)
  md += `## Results by Account\n\n`
  
  data.handles.forEach(handle => {
    const cleanHandle = handle.replace('@', '')
    const handlePosts = posts.filter(p => p.author === cleanHandle || p.source_handle === `@${cleanHandle}`)
    
    md += `### @${cleanHandle}\n\n`
    
    if (handlePosts.length === 0) {
      md += `No relevant posts found in the timeframe.\n\n`
    } else {
      md += `**Posts Found:** ${handlePosts.length}\n\n`
      handlePosts.forEach(post => {
        const text = (post.text || 'No text').slice(0, 80)
        md += `- [${text}...](${post.url || ''})\n`
      })
      md += `\n`
    }
    
    md += `---\n\n`
  })

  const filename = `twitter_report_${timestamp}.md`
  return { content: md, filename }
}

export const generatePolymarketResultsMarkdown = (keyword, results) => {
  const timestamp = getTimestamp()
  
  let md = `# Polymarket Search Results\n\n`
  md += `**Generated:** ${new Date().toISOString()}\n\n`
  md += `**Search Keyword:** ${keyword}\n\n`
  md += `**Markets Found:** ${results.length}\n\n`
  md += `---\n\n`

  results.forEach((market, index) => {
    md += `## ${index + 1}. ${market.title}\n\n`
    md += `- **Slug:** \`${market.slug}\`\n`
    md += `- **Volume:** $${market.volume.toLocaleString()}\n`
    md += `- **Liquidity:** $${market.liquidity.toLocaleString()}\n`
    md += `- **URL:** ${market.url}\n\n`
    md += `**Description:**\n${market.description}\n\n`
    md += `---\n\n`
  })

  // Sanitize keyword for filename
  const safeKeyword = keyword.replace(/[^a-z0-9]/gi, '_').slice(0, 20)
  const filename = `polymarket_search_${safeKeyword}_${timestamp}.md`
  return { content: md, filename }
}

export const generateMarketDetailsMarkdown = (details) => {
  const timestamp = getTimestamp()
  
  let md = `# Polymarket: ${details.title}\n\n`
  md += `**Generated:** ${new Date().toISOString()}\n\n`
  md += `**URL:** ${details.url}\n\n`
  md += `---\n\n`
  md += `## Overview\n\n`
  md += `${details.description}\n\n`
  md += `## Statistics\n\n`
  md += `| Metric | Value |\n`
  md += `|--------|-------|\n`
  md += `| Total Volume | $${details.volume.toLocaleString()} |\n`
  md += `| Liquidity | $${details.liquidity.toLocaleString()} |\n`
  md += `| End Date | ${details.endDate} |\n\n`
  
  if (details.outcomes && details.outcomes.length > 0) {
    md += `## Market Outcomes\n\n`
    md += `| Outcome | Probability | Volume |\n`
    md += `|---------|-------------|--------|\n`
    details.outcomes.forEach(outcome => {
      md += `| ${outcome.name} | ${(outcome.probability * 100).toFixed(1)}% | $${outcome.volume.toLocaleString()} |\n`
    })
    md += `\n`
  }

  // Sanitize slug/title for filename
  const safeName = (details.slug || details.title || 'market').replace(/[^a-z0-9]/gi, '_').slice(0, 30)
  const filename = `polymarket_${safeName}_${timestamp}.md`
  return { content: md, filename }
}

export const downloadMarkdown = (content, filename) => {
  // Ensure filename ends with .md
  let safeFilename = filename
  if (!safeFilename.toLowerCase().endsWith('.md')) {
    safeFilename = `${safeFilename}.md`
  }
  
  // Use text/plain to avoid browser MIME type issues
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.setAttribute('download', safeFilename)
  link.style.display = 'none'
  document.body.appendChild(link)
  link.click()
  
  // Cleanup after a short delay
  setTimeout(() => {
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }, 100)
}

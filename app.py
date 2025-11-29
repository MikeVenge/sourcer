"""
FastAPI Application for Sourcer
Deploy to Railway or run locally with: uvicorn app:app --reload
"""

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import asyncio
import time
import sys
import os

# Add lib to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))

from lib.polymarket_reader import (
    search_markets,
    fetch_event_by_slug,
    fetch_markets_by_tag,
    list_tags
)

from lib.twitter_reader import (
    run_cot_v2,
    extract_x_urls,
    fetch_all_posts,
    fetch_x_post_content
)

app = FastAPI(
    title="Sourcer API",
    description="Financial data aggregation from Polymarket and Twitter/X",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    """API root - returns available endpoints"""
    return {
        "name": "Sourcer API",
        "version": "1.0.0",
        "endpoints": {
            "/polymarket/search": "Search Polymarket events by keyword",
            "/polymarket/event/{slug}": "Get specific event by slug",
            "/polymarket/tags": "List all available tags",
            "/twitter/analyze": "Analyze Twitter accounts (POST)",
            "/twitter/post": "Get single post content",
            "/health": "Health check"
        }
    }


@app.get("/health")
def health():
    """Health check endpoint"""
    return {"status": "healthy"}


# ============================================================================
# Polymarket Endpoints
# ============================================================================

@app.get("/polymarket/search")
def polymarket_search(
    q: str = Query(..., description="Search keyword"),
    limit: int = Query(50, description="Max results"),
    include_closed: bool = Query(False, description="Include closed markets")
):
    """Search Polymarket events by keyword"""
    try:
        results = search_markets(q, limit, include_closed)
        return {
            "query": q,
            "count": len(results.get('events', [])),
            "events": results.get('events', []),
            "tags": results.get('tags', [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/polymarket/event/{slug}")
def polymarket_event(slug: str):
    """Get a specific Polymarket event by slug"""
    try:
        event = fetch_event_by_slug(slug)
        return event
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Event not found: {slug}")


@app.get("/polymarket/tags")
def polymarket_tags():
    """List all available Polymarket tags"""
    try:
        tags = list_tags()
        return {"count": len(tags), "tags": tags}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/polymarket/price-history/{slug}")
def polymarket_price_history(
    slug: str,
    market_index: int = Query(0, description="Market index within event"),
    fidelity: int = Query(1440, description="Resolution in minutes (1440=daily, 60=hourly)")
):
    """Get historical price data for a Polymarket market"""
    try:
        from lib.polymarket_reader import get_market_price_history
        result = get_market_price_history(slug, market_index, fidelity)
        if 'error' in result:
            raise HTTPException(status_code=404, detail=result['error'])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/polymarket/price-history-all/{slug}")
def polymarket_price_history_all(
    slug: str,
    fidelity: int = Query(60, description="Resolution in minutes (60=hourly, 1440=daily)")
):
    """Get historical price data for ALL markets in a Polymarket event"""
    try:
        from lib.polymarket_reader import get_all_markets_price_history
        result = get_all_markets_price_history(slug, fidelity)
        if 'error' in result:
            raise HTTPException(status_code=404, detail=result['error'])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Twitter/X Endpoints
# ============================================================================

# COT Session ID for Twitter analysis
TWITTER_COT_SESSION_ID = "692525b7fcc4aae81ac5eaf8"


class TwitterAnalysisRequest(BaseModel):
    """Request body for Twitter analysis"""
    handles: List[str]
    topic: str
    timeframe: int = 5  # days
    post_count: int = 10


class TwitterAnalysisResponse(BaseModel):
    """Response for Twitter analysis"""
    handles: List[str]
    topic: str
    timeframe: int
    total_posts: int
    posts: List[dict]
    errors: List[dict]


@app.post("/twitter/analyze")
def twitter_analyze(request: TwitterAnalysisRequest):
    """
    Analyze Twitter/X accounts using FinChat COT API.
    
    This calls run_cot_v2() for each handle, extracts X URLs,
    and fetches full post content using fxtwitter.com.
    """
    all_posts = []
    errors = []
    
    # Clean handles (remove @ if present)
    handles = [h.lstrip('@') for h in request.handles]
    
    # Convert timeframe to string format expected by COT API
    # Format: "last X days" or "last X week"
    timeframe_str = f"last {request.timeframe} days"
    
    for handle in handles:
        try:
            # Call COT API for this handle
            result = run_cot_v2(
                session_id=TWITTER_COT_SESSION_ID,
                accounts=[f"@{handle}"],
                topic=request.topic,
                timeframe=timeframe_str,
                post_count=request.post_count,
                timeout=300
            )
            
            # Extract X URLs from the result
            urls = extract_x_urls(result)
            
            if urls:
                # Fetch full content for each post
                posts = fetch_all_posts(urls)
                
                # Add source handle to each post
                for post in posts:
                    post['source_handle'] = f"@{handle}"
                    if 'error' not in post:
                        all_posts.append(post)
                    else:
                        errors.append({
                            'handle': handle,
                            'url': post.get('url'),
                            'error': post.get('error')
                        })
            
            # Small delay between handles to be respectful
            time.sleep(1)
            
        except Exception as e:
            errors.append({
                'handle': handle,
                'error': str(e)
            })
    
    # Sort posts by views (descending)
    all_posts.sort(key=lambda x: x.get('views', 0), reverse=True)
    
    return {
        "handles": handles,
        "topic": request.topic,
        "timeframe": request.timeframe,
        "total_posts": len(all_posts),
        "posts": all_posts,
        "errors": errors
    }


@app.get("/twitter/post")
def twitter_post(url: str = Query(..., description="X/Twitter post URL")):
    """
    Fetch content for a single X/Twitter post.
    Uses fxtwitter.com API to get full post data.
    """
    try:
        post = fetch_x_post_content(url)
        return post
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# YouTube API
# ============================================================================

class YouTubeRequest(BaseModel):
    url: str

def extract_video_id(url: str) -> str:
    """Extract video ID from various YouTube URL formats."""
    import re
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
        r'^([a-zA-Z0-9_-]{11})$'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError("Invalid YouTube URL")

@app.post("/youtube/transcript")
def youtube_transcript(request: YouTubeRequest):
    """
    Get transcript for a YouTube video.
    Returns transcript segments with timestamps.
    """
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
        import requests
        
        video_id = extract_video_id(request.url)
        
        # Get transcript
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
            # Try to get manual transcript first, then auto-generated
            transcript = None
            for t in transcript_list:
                if not t.is_generated:
                    transcript = t.fetch()
                    break
            
            if transcript is None:
                # Fall back to auto-generated
                transcript = transcript_list.find_generated_transcript(['en']).fetch()
                
        except NoTranscriptFound:
            # Try any available transcript
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
        
        # Get video info using oEmbed API
        video_info = {}
        try:
            oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
            resp = requests.get(oembed_url, timeout=10)
            if resp.ok:
                oembed = resp.json()
                video_info = {
                    "title": oembed.get("title", "Unknown"),
                    "channel": oembed.get("author_name", "Unknown"),
                    "thumbnail": oembed.get("thumbnail_url"),
                    "duration": sum(s.get('duration', 0) for s in transcript) if transcript else 0
                }
        except:
            video_info = {
                "title": f"Video {video_id}",
                "channel": "Unknown",
                "duration": sum(s.get('duration', 0) for s in transcript) if transcript else 0
            }
        
        return {
            "video_id": video_id,
            "video_info": video_info,
            "transcript": transcript
        }
        
    except TranscriptsDisabled:
        raise HTTPException(status_code=400, detail="Transcripts are disabled for this video")
    except NoTranscriptFound:
        raise HTTPException(status_code=404, detail="No transcript found for this video")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching transcript: {str(e)}")


# ============================================================================
# Run with uvicorn
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)



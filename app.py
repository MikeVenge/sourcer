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

import os

# API Keys - Set these as environment variables
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

def parse_duration_iso8601(duration: str) -> int:
    """Parse ISO 8601 duration (PT1H2M3S) to seconds."""
    import re
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
    if not match:
        return 0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds

def parse_caption_track(caption_content: str, format_type: str = "srv3") -> list:
    """Parse YouTube caption track XML into transcript segments."""
    import xml.etree.ElementTree as ET
    import html
    
    segments = []
    try:
        root = ET.fromstring(caption_content)
        for text_elem in root.findall('.//text'):
            start = float(text_elem.get('start', 0))
            dur = float(text_elem.get('dur', 0))
            text = text_elem.text or ''
            # Decode HTML entities
            text = html.unescape(text)
            if text.strip():
                segments.append({
                    'text': text.strip(),
                    'start': start,
                    'duration': dur
                })
    except ET.ParseError:
        pass
    return segments


@app.post("/youtube/transcript")
def youtube_transcript(request: YouTubeRequest):
    """
    Get transcript for a YouTube video.
    Downloads audio using yt-dlp and transcribes using Gemini.
    """
    import urllib.parse as urlparse
    import requests
    import subprocess
    import tempfile
    import os
    
    # Extract video ID from URL
    parsed = urlparse.urlparse(request.url)
    qs = urlparse.parse_qs(parsed.query)
    video_id = qs.get("v", [""])[0]
    
    # Handle youtu.be short URLs
    if not video_id and "youtu.be" in request.url:
        video_id = parsed.path.strip("/")
    
    # Handle embed URLs
    if not video_id and "/embed/" in request.url:
        video_id = parsed.path.split("/embed/")[-1].split("?")[0]
    
    if not video_id:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL. Could not extract video ID.")
    
    # Get video info using YouTube Data API v3
    video_info = {
        "title": f"Video {video_id}",
        "channel": "Unknown",
        "thumbnail": f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg",
        "duration": 0
    }
    
    try:
        api_url = "https://www.googleapis.com/youtube/v3/videos"
        params = {
            "part": "snippet,contentDetails",
            "id": video_id,
            "key": YOUTUBE_API_KEY
        }
        resp = requests.get(api_url, params=params, timeout=10)
        if resp.ok:
            data = resp.json()
            if data.get("items"):
                item = data["items"][0]
                snippet = item.get("snippet", {})
                content_details = item.get("contentDetails", {})
                
                video_info["title"] = snippet.get("title", video_info["title"])
                video_info["channel"] = snippet.get("channelTitle", video_info["channel"])
                
                thumbnails = snippet.get("thumbnails", {})
                if thumbnails.get("high"):
                    video_info["thumbnail"] = thumbnails["high"]["url"]
                elif thumbnails.get("medium"):
                    video_info["thumbnail"] = thumbnails["medium"]["url"]
                
                duration_str = content_details.get("duration", "PT0S")
                video_info["duration"] = parse_duration_iso8601(duration_str)
    except Exception as e:
        print(f"[YouTube] Error fetching video info: {e}")
    
    # Download audio using yt-dlp and transcribe with Gemini
    transcript = []
    
    with tempfile.TemporaryDirectory() as tmpdir:
        audio_file = os.path.join(tmpdir, f"{video_id}.mp3")
        
        print(f"")
        print(f"=" * 60)
        print(f"[YouTube] STEP 1/2: DOWNLOADING AUDIO")
        print(f"[YouTube] Video ID: {video_id}")
        print(f"=" * 60)
        
        # Download audio only using yt-dlp (low quality for smaller file size)
        cmd = [
            "yt-dlp",
            "-x",  # Extract audio
            "--audio-format", "mp3",
            "--audio-quality", "9",  # Lowest quality (smallest file, ~64kbps)
            "--postprocessor-args", "ffmpeg:-ac 1 -ar 16000",  # Mono, 16kHz (good for speech)
            "-o", audio_file,
            "--no-playlist",
            "--extractor-args", "youtube:player_client=default",
            f"https://www.youtube.com/watch?v={video_id}"
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                print(f"[YouTube] yt-dlp error: {result.stderr}")
                raise HTTPException(status_code=500, detail=f"Failed to download audio: {result.stderr[:200]}")
            
            # Check if file exists (yt-dlp might add extension)
            if not os.path.exists(audio_file):
                # Try with .mp3 already added by yt-dlp
                possible_files = [f for f in os.listdir(tmpdir) if f.endswith('.mp3')]
                if possible_files:
                    audio_file = os.path.join(tmpdir, possible_files[0])
                else:
                    raise HTTPException(status_code=500, detail="Audio file not found after download")
            
            file_size = os.path.getsize(audio_file)
            print(f"[YouTube] Downloaded audio: {file_size / 1024 / 1024:.2f} MB")
            
            # Transcribe using OpenAI Whisper API
            print(f"")
            print(f"=" * 60)
            print(f"[YouTube] STEP 2/2: TRANSCRIBING WITH AI")
            print(f"[YouTube] Using OpenAI Whisper API...")
            print(f"=" * 60)
            
            from openai import OpenAI
            
            client = OpenAI(api_key=OPENAI_API_KEY)
            
            # Use OpenAI's transcription API with retry for transient errors
            import time
            max_retries = 3
            last_error = None
            response = None
            
            for attempt in range(max_retries):
                try:
                    with open(audio_file, "rb") as audio:
                        response = client.audio.transcriptions.create(
                            model="whisper-1",
                            file=audio,
                            response_format="verbose_json"
                        )
                    break  # Success
                except Exception as e:
                    last_error = e
                    error_str = str(e)
                    # Retry on 502, 503, 500 errors (transient server issues)
                    if "502" in error_str or "503" in error_str or "500" in error_str or "Bad gateway" in error_str:
                        wait_time = 10 * (attempt + 1)  # 10s, 20s, 30s
                        print(f"[YouTube] OpenAI API error (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        raise  # Non-transient error, don't retry
            
            if response is None:
                raise last_error or Exception("Failed to transcribe after retries")
            
            print(f"")
            print(f"=" * 60)
            print(f"[YouTube] ✅ TRANSCRIPTION COMPLETE!")
            print(f"=" * 60)
            
            # Use segments from OpenAI response if available (has timestamps)
            if hasattr(response, 'segments') and response.segments:
                print(f"[YouTube] Got {len(response.segments)} segments with timestamps")
                for seg in response.segments:
                    transcript.append({
                        "text": seg.text.strip(),
                        "start": seg.start,
                        "duration": seg.end - seg.start
                    })
            else:
                # Fallback: split by sentences
                transcript_text = response.text.strip() if hasattr(response, 'text') else str(response)
                print(f"[YouTube] Transcription: {len(transcript_text)} characters")
                
                if transcript_text:
                    # Split into paragraphs as segments
                    paragraphs = [p.strip() for p in transcript_text.split('\n\n') if p.strip()]
                    if not paragraphs:
                        paragraphs = [transcript_text]
                    
                    # Estimate timing based on word count (roughly 150 words per minute)
                    current_time = 0.0
                    for para in paragraphs:
                        word_count = len(para.split())
                        duration = (word_count / 150) * 60  # Convert to seconds
                        transcript.append({
                            "text": para,
                            "start": current_time,
                            "duration": duration
                        })
                        current_time += duration
            
        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=504, detail="Audio download timed out")
        except HTTPException:
            raise
        except Exception as e:
            print(f"[YouTube] Error: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Transcription error: {str(e)}")
    
    if not transcript:
        raise HTTPException(status_code=500, detail="Failed to generate transcript")
    
    return {
        "video_id": video_id,
        "video_info": video_info,
        "transcript": transcript
    }


# ============================================================================
# Run with uvicorn
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)



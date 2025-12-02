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

# l2m2 Configuration for AI classification
L2M2_API_URL = os.getenv("L2M2_API_URL", "http://l2m2-production")
L2M2_COMPLETIONS_ENDPOINT = f"{L2M2_API_URL}/api/v1/completions/"

# NotebookLM Configuration
NOTEBOOKLM_PROJECT_NUMBER = os.getenv("NOTEBOOKLM_PROJECT_NUMBER", "511538466121")
NOTEBOOKLM_LOCATION = os.getenv("NOTEBOOKLM_LOCATION", "global")
NOTEBOOKLM_ENDPOINT_LOCATION = os.getenv("NOTEBOOKLM_ENDPOINT_LOCATION", "global-")
NOTEBOOKLM_SERVICE_ACCOUNT = os.getenv("NOTEBOOKLM_SERVICE_ACCOUNT", "notebooklm@graphic-charter-467314-n9.iam.gserviceaccount.com")

# V2 Investment Theme Notebook IDs - dynamically routed via AI classification
NOTEBOOKLM_NOTEBOOK_IDS = {
    "V2 - AI Infrastructure: Compute, Chips & Energy": "f25548c1-5a82-4ed8-a443-fe158924be3d",
    "V2 - Agentic Labor & Vibe Coding: The $10T Labor Arbitrage": "caaa9690-c773-4a60-96e7-ccf3f547210a",
    "V2 - Venture Metrics, Fund Strategy & Liquidity": "a2841480-b28d-4c6a-8545-433a322ad39a",
    "V2 - Incumbents vs. The Disruptors: AI Competition & GTM": "d388e457-604e-47c5-8f44-fa698eab3272",
    "V2 - Geopolitics, China & Sovereign AI (\"Red Stack\")": "fd8c00fb-2ae3-4eb5-8454-48142b6c6848",
    "V2 - The Frontier Model Race & Public–Private Fusion": "094f9eec-9420-4b3e-b5a7-6ee14342abee",
}

# Classification prompt for routing content to notebooks
NOTEBOOK_CLASSIFICATION_PROMPT = '''You are an AI content router for an investor's NotebookLM workspace.

Your job:

Given a user-supplied passage (a paragraph, article excerpt, memo, or transcript), decide which of the following investment-theme notebooks it belongs in.

General rules:

- You MAY assign a passage to multiple notebooks if it clearly fits more than one theme.

- Most passages should have 1–3 notebooks, not all of them.

- If no notebook is a clear fit, return an empty list.

- Focus on the underlying INVESTMENT THEME, not just surface keywords.

- When torn between two themes, choose the one that best explains the *core* thesis of the passage, and only add a second notebook if that theme is truly central.

Available notebooks and themes:

1) "V2 - AI Infrastructure: Compute, Chips & Energy"

   - Theme: Owning the physical and capital-intensive stack that powers AI: chips, data centers, networking, and energy.

   - Put content here when it is primarily about:

     - Chips / GPUs / TPUs / accelerators (e.g., Nvidia, HBM, CUDA, TPUs, custom silicon).

     - Data center buildout, hyperscaler capex, "Mag 7" infrastructure spending.

     - Energy as a bottleneck (power plants, nuclear, grid constraints).

     - Compute scarcity, who controls compute, and infra-driven revenue loops (e.g., round-tripping AI lab spend back into cloud + chips).

     - Infrastructure capital rotation that is clearly anchored around hardware/compute.

   - Strong cues: "Nvidia", "HBM", "GPU cluster", "TPU", "data center", "capex arms race", "energy bottleneck", "nuclear", "hyperscalers".

2) "V2 - Agentic Labor & Vibe Coding: The $10T Labor Arbitrage"

   - Theme: AI agents and "liquid software" that replace or radically augment human labor, especially in coding and enterprise workflows.

   - Put content here when it is primarily about:

     - AI agents doing work that humans used to do (SDRs, support agents, analysts, etc.).

     - Vibe coding / liquid software: non-technical users building software via LLMs.

     - Expansion of the developer / coder market via AI tools.

     - Application-layer "killer apps" where the core product is an AI agent or assistant, especially in coding.

     - Open-source agent business models (paid support, security, enterprise deployment).

   - Strong cues: "agents", "agentic", "vibe coding", "liquid software", "AI SDR", "AI support", "Cursor", "Replit", "Devin", "Copilot", "OpenHands".

3) "V2 - Venture Metrics, Fund Strategy & Liquidity"

   - Theme: How to price, fund, and structure AI companies and funds in a world where classic SaaS metrics break down.

   - Put content here when it is primarily about:

     - Gross profit dollars vs margins, impact of inference cost on unit economics.

     - Burn multiple, growth vs cash burn trade-offs.

     - Entry price vs outcome size (e.g., Scale AI / Alex Wang examples).

     - Fund size as strategy (mega-funds vs boutiques), and its implications.

     - Kingmaking via capital concentration in one startup.

     - Retail capital entering venture, perpetual secondary markets, liquidity for private companies.

     - Capital rotation examples when the main lens is portfolio construction or valuation, not hardware or models.

   - Strong cues: "gross margin", "gross profit dollars", "burn multiple", "entry price", "outcome size", "fund size", "mega fund", "secondary market", "liquidity", "retail investors".

4) "V2 - Incumbents vs. The Disruptors: AI Competition & GTM"

   - Theme: Competitive dynamics and game theory between established tech giants and AI-native startups.

   - Put content here when it is primarily about:

     - "War mode" vs "peacetime" cultures in big companies.

     - Whether incumbents (Google, Meta, Microsoft, etc.) are dead or resilient in AI.

     - Vertical battles: startups vs incumbents in specific sectors (e.g., legal tech, customer support).

     - Distribution, go-to-market strategies, and speed of integration.

     - Browser/search/app battles framed as startup vs incumbent.

   - Strong cues: "incumbent vs startup", "disruptor", "war mode", "game theory", "distribution", "go-to-market", "Harvey", "Sierra", "Intercom", "Brave".

5) "V2 - Geopolitics, China & Sovereign AI ("Red Stack")"

   - Theme: Nation-state AI strategies, export controls, and the bifurcation of US vs Chinese AI ecosystems.

   - Put content here when it is primarily about:

     - Beijing or Chinese regulators directing chip/model procurement (e.g., banning Nvidia, mandating Huawei/Cambricon).

     - The emergence of a "Red Stack" based on Chinese chips, mixed clusters, and open-weight models.

     - US export controls on chips or models, especially toward third-party countries (e.g., Malaysia).

     - Sovereign AI and countries choosing between US and Chinese stacks.

     - Price wars driven specifically by Chinese models attacking global markets.

   - Strong cues: "China", "Chinese", "Beijing", "ByteDance", "Alibaba", "Huawei", "Ascend", "Cambricon", "Red Stack", "export controls", "sovereign AI".

6) "V2 - The Frontier Model Race & Public–Private Fusion"

   - Theme: The capital-intensive race to build frontier models and the emerging fusion of state and private labs.

   - Put content here when it is primarily about:

     - Frontier model training (Gemini, GPT, xAI, etc.), especially pretraining vs post-training.

     - Technical and capital moats built by large training runs.

     - Government partnerships with labs (national labs providing data/compute, "AI Manhattan Project", etc.).

     - Subscriber economics or other scale economics specifically tied to funding frontier model development.

   - Strong cues: "frontier model", "Gemini 3", "GPT-4/5", "xAI", "pretraining", "post-training", "RLHF", "national labs", "AI Manhattan Project", "220M paying subscribers".

Conflict resolution and multi-tagging:

- Start by asking: "What is the MAIN question or investment thesis of this passage?"

- Assign that theme as the first notebook.

- Only add a second or third notebook if that theme is genuinely co-equal (e.g., Chinese export controls on chips → BOTH Geopolitics/China AND AI Infrastructure).

- Do NOT assign more than three notebooks for any single passage.

Output format:

- Return ONLY a JSON array of notebook titles you select, sorted by most to least relevant.

- Example:

  ["V2 - AI Infrastructure: Compute, Chips & Energy", "V2 - Geopolitics, China & Sovereign AI (\\"Red Stack\\")"]

---

PASSAGE TO CLASSIFY:

'''


def classify_content_for_notebooks(content: str) -> list:
    """
    Use l2m2 to classify content and determine which notebooks it should be routed to.
    
    Args:
        content: The markdown/text content to classify
        
    Returns:
        List of notebook names that the content should be sent to
    """
    import requests
    import json
    
    # Truncate content if too long (keep first ~8000 chars for classification)
    truncated_content = content[:8000] if len(content) > 8000 else content
    
    full_prompt = NOTEBOOK_CLASSIFICATION_PROMPT + truncated_content
    
    data = {
        "cached": True,
        "context": {
            "host": "sourcer",
            "local_user": "notebooklm-router",
            "property": "content-classification"
        },
        "models": [
            {
                "model": "gemini-2.5-pro",
                "temperature": 0.1,
            }
        ],
        "messages": [
            {
                "role": "user",
                "content": full_prompt
            }
        ],
    }
    
    try:
        print(f"[NotebookLM] Classifying content via l2m2...")
        response = requests.post(
            L2M2_COMPLETIONS_ENDPOINT,
            headers={'Content-Type': 'application/json'},
            json=data,
            timeout=60
        )
        
        response.raise_for_status()
        result = response.json()
        
        if result.get("errors") and result["errors"][0]:
            print(f"[NotebookLM] l2m2 error: {result['errors'][0]}")
            return []
        
        if "completions" in result and len(result["completions"]) > 0:
            completion_text = result["completions"][0]
            print(f"[NotebookLM] Classification result: {completion_text}")
            
            # Parse the JSON array from the response
            # Handle potential markdown code blocks
            cleaned = completion_text.strip()
            if cleaned.startswith("```"):
                # Remove markdown code block
                lines = cleaned.split("\n")
                cleaned = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
                cleaned = cleaned.strip()
            
            notebooks = json.loads(cleaned)
            
            if isinstance(notebooks, list):
                return notebooks
            else:
                print(f"[NotebookLM] Unexpected response format: {notebooks}")
                return []
        else:
            print("[NotebookLM] No completion in l2m2 response")
            return []
            
    except requests.exceptions.RequestException as e:
        print(f"[NotebookLM] l2m2 request error: {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"[NotebookLM] Failed to parse classification response as JSON: {e}")
        return []
    except Exception as e:
        print(f"[NotebookLM] Classification error: {e}")
        return []

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
# NotebookLM API
# ============================================================================

class NotebookLMRequest(BaseModel):
    source_name: str
    content: str
    source_type: str = "auto"  # Kept for backwards compatibility, but not used for routing
    content_type: str = "text"  # "text", "web", or "youtube"
    url: Optional[str] = None  # For web or youtube content


def _get_notebooklm_credentials():
    """Get Google Cloud credentials for NotebookLM API."""
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request
    import json
    
    credentials = None
    
    # Method 1: Try file path (GOOGLE_APPLICATION_CREDENTIALS)
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_path and os.path.exists(creds_path):
        print(f"[NotebookLM] Using credentials file: {creds_path}")
        credentials = service_account.Credentials.from_service_account_file(
            creds_path,
            scopes=['https://www.googleapis.com/auth/cloud-platform']
        )
    
    # Method 2: Try JSON string from environment variable
    if not credentials:
        service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
        if service_account_json:
            print(f"[NotebookLM] Using credentials from GOOGLE_SERVICE_ACCOUNT_JSON")
            sa_info = json.loads(service_account_json)
            credentials = service_account.Credentials.from_service_account_info(
                sa_info,
                scopes=['https://www.googleapis.com/auth/cloud-platform']
            )
    
    # Method 3: Fall back to default (GCP metadata service)
    if not credentials:
        print(f"[NotebookLM] Using default credentials (GCP metadata)")
        from google.auth import default
        credentials, project = default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
    
    # Refresh token if needed
    if not credentials.valid:
        credentials.refresh(Request())
    
    return credentials.token


def _add_source_to_notebook(notebook_id: str, notebook_name: str, source_name: str,
                            content: str, content_type: str, url: str, access_token: str) -> dict:
    """Add a source to a specific NotebookLM notebook."""
    import requests
    
    # Build the API URL
    api_url = (
        f"https://{NOTEBOOKLM_ENDPOINT_LOCATION}discoveryengine.googleapis.com"
        f"/v1alpha/projects/{NOTEBOOKLM_PROJECT_NUMBER}"
        f"/locations/{NOTEBOOKLM_LOCATION}"
        f"/notebooks/{notebook_id}/sources:batchCreate"
    )
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # Build the content based on type
    if content_type == "text":
        user_content = {
            "textContent": {
                "sourceName": source_name,
                "content": content
            }
        }
    elif content_type == "web":
        user_content = {
            "webContent": {
                "url": url,
                "sourceName": source_name
            }
        }
    elif content_type == "youtube":
        # NotebookLM handles YouTube URLs as webContent
        user_content = {
            "webContent": {
                "url": url,
                "sourceName": source_name
            }
        }
    else:
        return {"success": False, "notebook": notebook_name, "error": f"Unknown content type: {content_type}"}
    
    payload = {
        "userContents": [user_content]
    }
    
    print(f"[NotebookLM] Adding source to notebook: {notebook_name} ({notebook_id})")
    print(f"[NotebookLM] API URL: {api_url}")
    
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            print(f"[NotebookLM] ✅ Success! Source added to {notebook_name}")
            return {"success": True, "notebook": notebook_name, "result": result}
        else:
            error_detail = response.text[:500]
            print(f"[NotebookLM] ❌ Error for {notebook_name}: {response.status_code} - {error_detail}")
            return {"success": False, "notebook": notebook_name, "error": error_detail}
            
    except requests.exceptions.RequestException as e:
        print(f"[NotebookLM] ❌ Request error for {notebook_name}: {e}")
        return {"success": False, "notebook": notebook_name, "error": str(e)}


@app.post("/notebooklm/add-source")
def notebooklm_add_source(request: NotebookLMRequest):
    """
    Add a source to NotebookLM notebooks using AI classification.
    
    The content is analyzed by Gemini Pro 2.5 to determine which investment-theme
    notebooks it should be routed to. Content can be sent to multiple notebooks
    (typically 1-3) based on the themes detected.
    
    Supports:
    - Text content (raw text)
    - Web content (URL)
    - YouTube video (URL)
    
    Uses service account authentication.
    """
    import requests as req_lib
    
    if not NOTEBOOKLM_PROJECT_NUMBER:
            raise HTTPException(
            status_code=500, 
            detail="NotebookLM not configured. Set NOTEBOOKLM_PROJECT_NUMBER environment variable."
        )
    
    # Validate content type requirements
    if request.content_type in ["web", "youtube"] and not request.url:
        raise HTTPException(status_code=400, detail=f"URL required for {request.content_type} content")
    
    # Step 1: Classify content using l2m2/Gemini Pro 2.5
    print(f"")
    print(f"=" * 60)
    print(f"[NotebookLM] STEP 1/2: CLASSIFYING CONTENT")
    print(f"[NotebookLM] Source name: {request.source_name}")
    print(f"[NotebookLM] Content type: {request.content_type}")
    print(f"=" * 60)
    
    classified_notebooks = classify_content_for_notebooks(request.content)
    
    if not classified_notebooks:
        print(f"[NotebookLM] ⚠️ No notebooks matched for this content")
        return {
            "success": False,
            "message": "Content did not match any investment-theme notebooks",
            "classified_notebooks": [],
            "results": []
        }
    
    print(f"[NotebookLM] Classified into {len(classified_notebooks)} notebook(s): {classified_notebooks}")
    
    # Step 2: Get credentials
    try:
        access_token = _get_notebooklm_credentials()
    except Exception as e:
        print(f"[NotebookLM] Error getting service account token: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to authenticate with service account: {str(e)}. "
                   "Set GOOGLE_APPLICATION_CREDENTIALS (file path) or "
                   "GOOGLE_SERVICE_ACCOUNT_JSON (JSON string) environment variable."
        )
    
    # Step 3: Send to each classified notebook
    print(f"")
    print(f"=" * 60)
    print(f"[NotebookLM] STEP 2/2: SENDING TO NOTEBOOKS")
    print(f"=" * 60)
    
    results = []
    success_count = 0
    
    for notebook_name in classified_notebooks:
        notebook_id = NOTEBOOKLM_NOTEBOOK_IDS.get(notebook_name)
        
        if not notebook_id:
            print(f"[NotebookLM] ⚠️ Unknown notebook name: {notebook_name}")
            results.append({
                "success": False, 
                "notebook": notebook_name, 
                "error": "Notebook not found in configuration"
            })
            continue
        
        result = _add_source_to_notebook(
            notebook_id=notebook_id,
            notebook_name=notebook_name,
            source_name=request.source_name,
            content=request.content,
            content_type=request.content_type,
            url=request.url,
            access_token=access_token
        )
        
        results.append(result)
        if result["success"]:
            success_count += 1
    
    # Summary
    print(f"")
    print(f"=" * 60)
    print(f"[NotebookLM] ✅ COMPLETE: {success_count}/{len(classified_notebooks)} notebooks updated")
    print(f"=" * 60)
    
    return {
        "success": success_count > 0,
        "message": f"Source added to {success_count}/{len(classified_notebooks)} notebooks",
        "classified_notebooks": classified_notebooks,
        "results": results
    }


@app.get("/notebooklm/config")
def notebooklm_config():
    """
    Get NotebookLM configuration status.
    """
    return {
        "configured": bool(NOTEBOOKLM_PROJECT_NUMBER),
        "project_number": NOTEBOOKLM_PROJECT_NUMBER[:4] + "..." if NOTEBOOKLM_PROJECT_NUMBER else None,
        "location": NOTEBOOKLM_LOCATION,
        "endpoint_location": NOTEBOOKLM_ENDPOINT_LOCATION
    }


# ============================================================================
# Run with uvicorn
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)



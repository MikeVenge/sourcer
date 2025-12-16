"""
FastAPI Application for Sourcer
Deploy to Railway or run locally with: uvicorn app:app --reload
"""

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
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
# Note: When allow_credentials=True, you cannot use allow_origins=["*"]
# Must explicitly list origins or set allow_credentials=False
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://sourcer-six.vercel.app",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
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
    """Health check endpoint for Railway and monitoring"""
    return {
        "status": "healthy",
        "service": "sourcer-api",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }


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
    timeframe: int = 1  # weeks
    post_count: int = 50
    processing_mode: Optional[str] = "batch"  # "batch" or "individual"


class TwitterAnalysisResponse(BaseModel):
    """Response for Twitter analysis"""
    handles: List[str]
    topic: str
    timeframe: int
    total_posts: int
    posts: List[dict]
    errors: List[dict]


@app.post("/twitter/analyze")
@app.post("/twitter/analyze/")  # Handle trailing slash
def twitter_analyze(request: TwitterAnalysisRequest):
    """
    Analyze Twitter/X accounts using FinChat COT API.
    
    Supports two processing modes:
    - "batch": Calls run_cot_v2() once with all handles (faster)
    - "individual": Calls run_cot_v2() once per handle (more detailed tracking)
    
    Extracts X URLs and fetches full post content using fxtwitter.com.
    """
    all_posts = []
    errors = []
    
    # Clean handles (remove @ if present)
    handles = [h.lstrip('@') for h in request.handles]
    total_accounts = len(handles)
    
    # Convert timeframe to string format expected by COT API
    # Format: "last X weeks" or "last X week"
    if request.timeframe == 1:
        timeframe_str = "last 1 week"
    else:
        timeframe_str = f"last {request.timeframe} weeks"
    
    # Determine processing mode (default to batch)
    processing_mode = request.processing_mode or "batch"
    
    print(f"")
    print(f"=" * 60)
    print(f"[Twitter] STARTING ANALYSIS")
    print(f"=" * 60)
    print(f"[Twitter] Processing mode: {processing_mode.upper()}")
    print(f"[Twitter] Total accounts: {total_accounts}")
    print(f"[Twitter] Accounts: {', '.join([f'@{h}' for h in handles])}")
    print(f"[Twitter] Topic: {request.topic}")
    print(f"[Twitter] Timeframe: {timeframe_str}")
    print(f"[Twitter] Max posts per account: {request.post_count}")
    print(f"=" * 60)
    
    if processing_mode == "individual":
        # Process each handle individually (original way)
        for idx, handle in enumerate(handles, 1):
            print(f"")
            print(f"[Twitter] Processing account {idx}/{total_accounts}: @{handle}")
            print(f"[Twitter] ──────────────────────────────────────────────")
            
            try:
                # Call COT API for this handle
                print(f"[Twitter] Calling FinChat COT API...")
                result = run_cot_v2(
                    session_id=TWITTER_COT_SESSION_ID,
                    accounts=[f"@{handle}"],
                    topic=request.topic,
                    timeframe=timeframe_str,
                    post_count=request.post_count,
                    timeout=300
                )
                
                # Extract X URLs from the result
                print(f"[Twitter] Extracting X URLs from COT result...")
                urls = extract_x_urls(result)
                print(f"[Twitter] Found {len(urls)} X URLs for @{handle}")
                
                if urls:
                    # Fetch full content for each post
                    print(f"[Twitter] Fetching post content ({len(urls)} posts)...")
                    posts = fetch_all_posts(urls)
                    
                    successful_posts = 0
                    failed_posts = 0
                    
                    # Add source handle to each post
                    for post in posts:
                        post['source_handle'] = f"@{handle}"
                        if 'error' not in post:
                            all_posts.append(post)
                            successful_posts += 1
                        else:
                            failed_posts += 1
                            errors.append({
                                'handle': handle,
                                'url': post.get('url'),
                                'error': post.get('error')
                            })
                    
                    print(f"[Twitter] ✅ @{handle}: {successful_posts} posts fetched successfully, {failed_posts} failed")
                    print(f"[Twitter] Total posts collected so far: {len(all_posts)}")
                else:
                    print(f"[Twitter] ⚠️  @{handle}: No URLs found in COT result")
                
                # Small delay between handles to be respectful
                time.sleep(1)
                
            except Exception as e:
                print(f"[Twitter] ❌ @{handle}: Error - {str(e)}")
                errors.append({
                    'handle': handle,
                    'error': str(e)
                })
    
    else:
        # Process all handles in batch (current way)
        try:
            # Call COT API once with all handles
            print(f"")
            print(f"[Twitter] Calling FinChat COT API with all {total_accounts} handles...")
            print(f"[Twitter] ──────────────────────────────────────────────")
            
            result = run_cot_v2(
                session_id=TWITTER_COT_SESSION_ID,
                accounts=[f"@{h}" for h in handles],  # All handles at once
                topic=request.topic,
                timeframe=timeframe_str,
                post_count=request.post_count,
                timeout=300
            )
            
            # Extract X URLs from the result
            print(f"[Twitter] Extracting X URLs from COT result...")
            urls = extract_x_urls(result)
            print(f"[Twitter] Found {len(urls)} X URLs total")
            
            if urls:
                # Fetch full content for each post
                print(f"[Twitter] Fetching post content ({len(urls)} posts)...")
                posts = fetch_all_posts(urls)
                
                successful_posts = 0
                failed_posts = 0
                
                # Match posts to handles based on author field
                handle_set = {h.lower() for h in handles}  # For case-insensitive matching
                
                for post in posts:
                    if 'error' not in post:
                        # Try to match post author to one of our handles
                        author = post.get('author', '').lower().lstrip('@')
                        matched_handle = None
                        
                        # Find matching handle
                        for handle in handles:
                            if author == handle.lower():
                                matched_handle = handle
                                break
                        
                        # If no exact match, try to find partial match
                        if not matched_handle:
                            for handle in handles:
                                if handle.lower() in author or author in handle.lower():
                                    matched_handle = handle
                                    break
                        
                        # Add source handle (use matched handle or mark as unknown)
                        if matched_handle:
                            post['source_handle'] = f"@{matched_handle}"
                        else:
                            # If we can't match, check if author is in our handle list
                            post['source_handle'] = f"@{author}" if author else "Unknown"
                        
                        all_posts.append(post)
                        successful_posts += 1
                    else:
                        failed_posts += 1
                        errors.append({
                            'handle': 'unknown',
                            'url': post.get('url'),
                            'error': post.get('error')
                        })
                
                print(f"[Twitter] ✅ Processing complete: {successful_posts} posts fetched successfully, {failed_posts} failed")
                print(f"[Twitter] Total posts collected: {len(all_posts)}")
            else:
                print(f"[Twitter] ⚠️  No URLs found in COT result")
            
        except Exception as e:
            print(f"[Twitter] ❌ Error processing handles: {str(e)}")
            import traceback
            traceback.print_exc()
            errors.append({
                'handle': 'all',
                'error': str(e)
            })
    
    print(f"")
    print(f"=" * 60)
    print(f"[Twitter] ANALYSIS COMPLETE")
    print(f"=" * 60)
    print(f"[Twitter] Processing mode: {processing_mode.upper()}")
    print(f"[Twitter] Accounts analyzed: {total_accounts}")
    print(f"[Twitter] Total posts collected: {len(all_posts)}")
    print(f"[Twitter] Total errors: {len(errors)}")
    if errors:
        for error in errors:
            print(f"[Twitter]   Error: {error.get('handle', 'unknown')} - {error.get('error', 'Unknown error')}")
    print(f"=" * 60)
    
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
SEARCHAPI_API_KEY = os.getenv("SEARCHAPI_API_KEY", "AEqiQPXdmzJo1Zdu8o9s1GJQ")

# l2m2 Configuration for AI classification (OpenAI SDK compatible)
L2M2_BASE_URL = "https://l2m2.adgo-infra.com/api/v4"
L2M2_API_KEY = "l2m2-uyGbDWdn6TGCXvAISfkfHdGd6Z7UsmoCtLD4y1ARRRU"

# Bucketeer Configuration
BUCKETEER_BASE_URL = os.getenv("BUCKETEER_BASE_URL", "https://bucketeer.adgo-infra.com/")
BUCKETEER_API_KEY = os.getenv("BUCKETEER_API_KEY", "bcktr-wxFrNg7Co6MbtvQdtpk39lK0TPALbW5T")


def clean_unicode_for_bucketeer(text: str) -> str:
    """
    Clean Unicode surrogate characters from text for Bucketeer API.
    Bucketeer doesn't allow surrogate characters (emojis encoded as surrogate pairs).
    
    Args:
        text: The text content to clean
        
    Returns:
        Cleaned text without surrogate characters
    """
    try:
        # Encode to UTF-8 with surrogatepass to handle surrogates, then decode with replace
        # This removes invalid surrogate pairs
        cleaned = text.encode('utf-8', 'surrogatepass').decode('utf-8', 'replace')
        return cleaned
    except Exception as e:
        print(f"[Bucketeer] Warning: Error cleaning Unicode: {e}")
        # Fallback: try to remove surrogate characters manually
        try:
            # Remove surrogate pairs (U+D800 to U+DFFF)
            cleaned = ''.join(
                char for char in text 
                if not ('\ud800' <= char <= '\udfff')
            )
            return cleaned
        except:
            # Last resort: return as-is
            return text

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
    Use l2m2 (via OpenAI SDK) to classify content and determine which notebooks it should be routed to.
    
    Args:
        content: The markdown/text content to classify
        
    Returns:
        List of notebook names that the content should be sent to
    """
    from openai import OpenAI
    import json
    
    # Clean Unicode surrogate characters before processing
    cleaned_content = clean_unicode_for_bucketeer(content)
    
    # Truncate content if too long (keep first ~8000 chars for classification)
    truncated_content = cleaned_content[:8000] if len(cleaned_content) > 8000 else cleaned_content
    
    full_prompt = NOTEBOOK_CLASSIFICATION_PROMPT + truncated_content + "\n\nIMPORTANT: Respond ONLY with a JSON array of notebook titles. No other text."
    
    try:
        print(f"[NotebookLM] Classifying content via l2m2 (OpenAI SDK)...")
        print(f"[NotebookLM] Content length: {len(truncated_content)} chars")
        
        client = OpenAI(
            base_url=L2M2_BASE_URL,
            api_key=L2M2_API_KEY
        )
        
        response = client.responses.create(
            model="gemini-2.5-flash",
            input=full_prompt,
            temperature=0.1,
        )
        
        completion_text = response.output_text
        print(f"[NotebookLM] Classification result: {completion_text[:200]}...")
        
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
            print(f"[NotebookLM] Parsed {len(notebooks)} notebooks: {notebooks}")
            return notebooks
        else:
            print(f"[NotebookLM] Unexpected response format: {notebooks}")
            return []
            
    except json.JSONDecodeError as e:
        print(f"[NotebookLM] Failed to parse classification response as JSON: {e}")
        print(f"[NotebookLM] Raw response: {completion_text[:200] if completion_text else 'None'}")
        return []
    except Exception as e:
        print(f"[NotebookLM] Classification error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
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
    Get transcript for a YouTube video using SearchAPI.io YouTube Transcripts API.
    See: https://www.searchapi.io/docs/youtube-transcripts
    """
    import urllib.parse as urlparse
    import requests
    
    if not SEARCHAPI_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="SearchAPI.io API not configured. Set SEARCHAPI_API_KEY environment variable."
        )
    
    # Extract video ID from URL
    parsed = urlparse.urlparse(request.url)
    qs = urlparse.parse_qs(parsed.query)
    video_id = qs.get("v", [""])[0]
    
    if not video_id and "youtu.be" in request.url:
        video_id = parsed.path.strip("/")
    
    if not video_id and "/embed/" in request.url:
        video_id = parsed.path.split("/embed/")[-1].split("?")[0]
    
    if not video_id:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL. Could not extract video ID.")
    
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    
    print(f"")
    print(f"=" * 60)
    print(f"[YouTube] FETCHING TRANSCRIPT VIA SEARCHAPI.IO")
    print(f"[YouTube] Video ID: {video_id}")
    print(f"[YouTube] URL: {video_url}")
    print(f"=" * 60)
    
    try:
        # Call SearchAPI.io YouTube Transcripts API
        # API Documentation: https://www.searchapi.io/docs/youtube-transcripts
        # Engine name is "youtube_transcripts" (plural)
        api_url = "https://www.searchapi.io/api/v1/search"
        params = {
            "engine": "youtube_transcripts",  # Correct: plural form
            "video_id": video_id,
            "api_key": SEARCHAPI_API_KEY,
            "lang": "en"  # Default to English, can be made configurable
        }
        
        print(f"[YouTube] Calling SearchAPI.io...")
        print(f"[YouTube] Video ID: {video_id}")
        print(f"[YouTube] API URL: {api_url}")
        try:
            response = requests.get(api_url, params=params, timeout=120)
        except requests.exceptions.Timeout:
            print(f"[YouTube] SearchAPI.io request timed out after 120 seconds")
            raise HTTPException(
                status_code=504,
                detail="YouTube transcript service timed out. The service may be experiencing high load or quota issues. Please try again later."
            )
        except requests.exceptions.ConnectionError as e:
            print(f"[YouTube] SearchAPI.io connection error: {e}")
            raise HTTPException(
                status_code=503,
                detail=f"YouTube transcript service unavailable: {str(e)}"
            )
        
        # Try to parse JSON response even if status is not OK
        try:
            data = response.json()
        except ValueError:
            # If JSON parsing fails, use text response
            error_detail = response.text[:500]
            print(f"[YouTube] SearchAPI.io error: {response.status_code} - {error_detail}")
            raise HTTPException(
                status_code=500,
                detail=f"SearchAPI.io API error: {error_detail}"
            )
        
        # Check for errors in response (even if HTTP status was OK)
        if "error" in data:
            error_msg = data.get("error", "Unknown error")
            print(f"[YouTube] SearchAPI.io error in response: {error_msg}")
            
            # Check for quota/plan errors
            if "quota" in error_msg.lower() or "upgrade" in error_msg.lower() or "searches for the month" in error_msg.lower():
                raise HTTPException(
                    status_code=402,
                    detail=f"YouTube transcript service quota exceeded. {error_msg}"
                )
            
            # Check for language-related errors
            available_languages = data.get("available_languages", [])
            if available_languages:
                lang_list = ", ".join([f"{lang['name']} ({lang['lang']})" for lang in available_languages])
                error_msg += f" Available languages: {lang_list}"
            
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Check HTTP status after parsing JSON
        if not response.ok:
            error_detail = response.text[:500]
            print(f"[YouTube] SearchAPI.io HTTP error: {response.status_code} - {error_detail}")
            raise HTTPException(
                status_code=500,
                detail=f"SearchAPI.io API error (HTTP {response.status_code}): {error_detail}"
            )
        
        # Extract transcript
        # API returns "transcripts" (plural) array
        transcripts = data.get("transcripts", [])
        
        if not transcripts:
            # Check if there's an error message about available languages
            available_languages = data.get("available_transcripts_languages", [])
            if available_languages:
                lang_list = ", ".join([f"{lang.get('name', lang.get('lang', ''))} ({lang.get('lang', '')})" for lang in available_languages])
                raise HTTPException(
                    status_code=404, 
                    detail=f"No transcript available for this video in the requested language (en). Available languages: {lang_list}"
                )
            raise HTTPException(status_code=404, detail="No transcript available for this video")
        
        print(f"[YouTube] ✅ Got {len(transcripts)} transcript segments")
        
        # Format transcript to match expected structure
        transcript = []
        for segment in transcripts:
            transcript.append({
                "text": segment.get("text", "").strip(),
                "start": segment.get("start", 0),
                "duration": segment.get("duration", 0)
            })
        
        # Get video info from metadata if available, otherwise use defaults
        search_metadata = data.get("search_metadata", {})
        request_url = search_metadata.get("request_url", video_url)
        
        # Basic video info (SearchAPI.io doesn't provide full video metadata)
        video_info = {
            "title": f"Video {video_id}",  # SearchAPI.io doesn't provide title
            "channel": "Unknown",  # SearchAPI.io doesn't provide channel
            "thumbnail": f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg",
            "duration": 0,  # SearchAPI.io doesn't provide duration
            "views": 0,  # SearchAPI.io doesn't provide views
            "likes": 0,  # SearchAPI.io doesn't provide likes
            "description": "",  # SearchAPI.io doesn't provide description
            "date_posted": ""  # SearchAPI.io doesn't provide date
        }
        
        print(f"[YouTube] Title: {video_info['title']}")
        print(f"[YouTube] Transcript segments: {len(transcript)}")
        print(f"[YouTube] Original URL: {request.url}")
        
        # Print first 200 words of transcript
        all_text = " ".join([segment.get("text", "") for segment in transcript])
        words = all_text.split()
        first_200_words = " ".join(words[:200])
        print(f"[YouTube] First 200 words of transcript: {first_200_words}")
        
        return {
            "video_id": video_id,
            "video_info": video_info,
            "transcript": transcript,
            "original_url": request.url  # Preserve the original user-entered URL
        }
        
    except HTTPException:
        raise
    except requests.exceptions.Timeout:
        print(f"[YouTube] Request timeout error")
        raise HTTPException(
            status_code=504,
            detail="YouTube transcript service timed out. Please try again later."
        )
    except requests.exceptions.RequestException as e:
        print(f"[YouTube] Request error: {e}")
        raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")
    except Exception as e:
        print(f"[YouTube] Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# ============================================================================
# Reddit API
# ============================================================================

class RedditAnalysisRequest(BaseModel):
    subreddit: str
    post_count: int = 10  # min 5, max 20

@app.post("/reddit/analyze")
def reddit_analyze(request: RedditAnalysisRequest):
    """
    Fetch posts and comments from a Reddit subreddit.
    Uses Reddit's public JSON API (no authentication required).
    """
    import requests
    
    # Validate post_count
    post_count = max(5, min(20, request.post_count))
    
    # Clean subreddit name (remove r/ prefix if present)
    subreddit = request.subreddit.strip()
    if subreddit.startswith('r/'):
        subreddit = subreddit[2:]
    if subreddit.startswith('/r/'):
        subreddit = subreddit[3:]
    
    print(f"[Reddit] Fetching {post_count} posts from r/{subreddit}")
    
    all_posts = []
    errors = []
    
    try:
        # Fetch hot posts from subreddit using Reddit's public JSON API
        headers = {
            'User-Agent': 'Sourcer/1.0 (Market Intelligence Platform)'
        }
        
        # Get posts
        posts_url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={post_count}"
        print(f"[Reddit] Fetching posts from: {posts_url}")
        
        response = requests.get(posts_url, headers=headers, timeout=30)
        
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Subreddit r/{subreddit} not found")
        elif response.status_code == 403:
            raise HTTPException(status_code=403, detail=f"Subreddit r/{subreddit} is private or quarantined")
        elif response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=f"Reddit API error: {response.status_code}")
        
        data = response.json()
        posts_data = data.get('data', {}).get('children', [])
        
        print(f"[Reddit] Found {len(posts_data)} posts")
        
        for post_item in posts_data:
            post = post_item.get('data', {})
            
            # Skip stickied/pinned posts
            if post.get('stickied', False):
                continue
            
            post_id = post.get('id')
            permalink = post.get('permalink', '')
            
            # Fetch comments for this post
            comments = []
            try:
                comments_url = f"https://www.reddit.com{permalink}.json?limit=10&depth=2"
                comments_response = requests.get(comments_url, headers=headers, timeout=15)
                
                if comments_response.status_code == 200:
                    comments_data = comments_response.json()
                    if len(comments_data) > 1:
                        comment_children = comments_data[1].get('data', {}).get('children', [])
                        for comment_item in comment_children[:10]:  # Top 10 comments
                            comment = comment_item.get('data', {})
                            if comment.get('body') and comment.get('kind') != 'more':
                                comments.append({
                                    'author': comment.get('author', '[deleted]'),
                                    'body': comment.get('body', ''),
                                    'score': comment.get('score', 0),
                                    'created_utc': comment.get('created_utc', 0),
                                    'permalink': f"https://reddit.com{comment.get('permalink', '')}"
                                })
                
                # Small delay to be respectful to Reddit's API
                time.sleep(0.5)
                
            except Exception as e:
                print(f"[Reddit] Error fetching comments for post {post_id}: {e}")
            
            # Build post object
            post_obj = {
                'id': post_id,
                'title': post.get('title', ''),
                'author': post.get('author', '[deleted]'),
                'selftext': post.get('selftext', ''),
                'url': f"https://reddit.com{permalink}",
                'score': post.get('score', 0),
                'upvote_ratio': post.get('upvote_ratio', 0),
                'num_comments': post.get('num_comments', 0),
                'created_utc': post.get('created_utc', 0),
                'subreddit': subreddit,
                'is_self': post.get('is_self', True),
                'link_url': post.get('url', '') if not post.get('is_self', True) else None,
                'thumbnail': post.get('thumbnail', ''),
                'flair': post.get('link_flair_text', ''),
                'comments': comments
            }
            
            all_posts.append(post_obj)
        
        print(f"[Reddit] Successfully fetched {len(all_posts)} posts with comments")
        
        # Sort by score (descending)
        all_posts.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        return {
            "subreddit": subreddit,
            "post_count": len(all_posts),
            "posts": all_posts,
            "errors": errors
        }
        
    except HTTPException:
        raise
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Reddit API timeout")
    except requests.exceptions.RequestException as e:
        print(f"[Reddit] Request error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch from Reddit: {str(e)}")
    except Exception as e:
        print(f"[Reddit] Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# NotebookLM API
# ============================================================================

class NotebookLMRequest(BaseModel):
    source_name: str
    content: str
    source_type: str = "auto"  # Kept for backwards compatibility, but not used for routing
    content_type: str = "text"  # "text", "web", or "youtube"
    url: Optional[str] = None  # For web or youtube content
    notebook_ids: Optional[List[str]] = None  # Optional list of notebook IDs to send to (if not provided, uses AI classification)


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
        # Use webContent for YouTube URLs - NotebookLM can process YouTube URLs via webContent
        # The API doesn't recognize "url" field in videoContent, so we use webContent instead
        user_content = {
            "webContent": {
                "url": url,
                "sourceName": source_name
            }
        }
    else:
        return {"success": False, "notebook": notebook_name, "notebook_id": notebook_id, "error": f"Unknown content type: {content_type}"}
    
    payload = {
        "userContents": [user_content]
    }
    
    import json
    
    print(f"\n{'='*80}")
    print(f"[NotebookLM] EXACT API CALL DETAILS")
    print(f"{'='*80}")
    print(f"[NotebookLM] Notebook: {notebook_name} ({notebook_id})")
    print(f"[NotebookLM] Content Type: {content_type}")
    print(f"[NotebookLM] Source Name: {source_name}")
    print(f"[NotebookLM] URL being sent: {url}")
    print(f"\n[NotebookLM] API Endpoint:")
    print(f"  METHOD: POST")
    print(f"  URL: {api_url}")
    print(f"\n[NotebookLM] Headers:")
    print(f"  Authorization: Bearer {access_token[:30]}...{access_token[-10:] if len(access_token) > 40 else ''}")
    print(f"  Content-Type: {headers['Content-Type']}")
    print(f"\n[NotebookLM] Payload (JSON):")
    print(json.dumps(payload, indent=2))
    print(f"\n[NotebookLM] CURL Equivalent:")
    print(f"curl -X POST \\")
    print(f"  -H \"Authorization: Bearer $(gcloud auth print-access-token)\" \\")
    print(f"  -H \"Content-Type: application/json\" \\")
    print(f"  \"{api_url}\" \\")
    print(f"  -d '{json.dumps(payload)}'")
    print(f"{'='*80}\n")
    
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=60)
        
        print(f"[NotebookLM] Response Status: {response.status_code}")
        print(f"[NotebookLM] Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"[NotebookLM] Response Body:")
            print(json.dumps(result, indent=2))
            print(f"[NotebookLM] ✅ Success! Source added to {notebook_name}")
            return {"success": True, "notebook": notebook_name, "notebook_id": notebook_id, "result": result}
        else:
            error_detail = response.text
            print(f"[NotebookLM] Error Response:")
            print(error_detail)
            print(f"[NotebookLM] ❌ Error for {notebook_name}: {response.status_code}")
            return {"success": False, "notebook": notebook_name, "notebook_id": notebook_id, "error": error_detail[:500]}
            
    except requests.exceptions.RequestException as e:
        print(f"[NotebookLM] ❌ Request error for {notebook_name}: {e}")
        return {"success": False, "notebook": notebook_name, "notebook_id": notebook_id, "error": str(e)}


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
    import traceback
    
    print(f"[NotebookLM] === REQUEST RECEIVED ===")
    print(f"[NotebookLM] source_name: {request.source_name}")
    print(f"[NotebookLM] content_type: {request.content_type}")
    print(f"[NotebookLM] content_length: {len(request.content) if request.content else 0}")
    
    if not NOTEBOOKLM_PROJECT_NUMBER:
        raise HTTPException(
            status_code=500, 
            detail="NotebookLM not configured. Set NOTEBOOKLM_PROJECT_NUMBER environment variable."
        )
    
    # Validate content type requirements
    if request.content_type in ["web", "youtube"] and not request.url:
        raise HTTPException(status_code=400, detail=f"URL required for {request.content_type} content")
    
    # Step 1: Determine which notebooks to use
    print(f"")
    print(f"=" * 60)
    print(f"[NotebookLM] Source name: {request.source_name}")
    print(f"[NotebookLM] Content type: {request.content_type}")
    print(f"=" * 60)
    
    # If notebook_ids are provided, use those; otherwise classify
    if request.notebook_ids and len(request.notebook_ids) > 0:
        print(f"[NotebookLM] Using user-selected notebooks: {request.notebook_ids}")
        # Convert notebook IDs to names for display
        notebook_id_to_name = {v: k for k, v in NOTEBOOKLM_NOTEBOOK_IDS.items()}
        selected_notebooks = []
        for notebook_id in request.notebook_ids:
            notebook_name = notebook_id_to_name.get(notebook_id)
            if notebook_name:
                selected_notebooks.append(notebook_name)
            else:
                print(f"[NotebookLM] ⚠️ Unknown notebook ID: {notebook_id}")
        classified_notebooks = selected_notebooks
    else:
        # Step 1: Classify content using l2m2/Gemini Pro 2.5
        print(f"[NotebookLM] STEP 1/2: CLASSIFYING CONTENT")
        print(f"[NotebookLM] Content length: {len(request.content) if request.content else 0} chars")
        print(f"[NotebookLM] Content preview: {request.content[:500] if request.content else '(empty)'}...")
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
    
    # Step 2: Get credentials and send to notebooks
    print(f"")
    print(f"=" * 60)
    print(f"[NotebookLM] SENDING TO NOTEBOOKS")
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
                "notebook_id": None,
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
    
    # Build a mapping of notebook names to IDs for frontend use
    notebook_mapping = {}
    for notebook_name in classified_notebooks:
        notebook_id = NOTEBOOKLM_NOTEBOOK_IDS.get(notebook_name)
        if notebook_id:
            notebook_mapping[notebook_name] = notebook_id
    
    return {
        "success": success_count > 0,
        "message": f"Source added to {success_count}/{len(classified_notebooks)} notebooks",
        "classified_notebooks": classified_notebooks,
        "notebook_mapping": notebook_mapping,  # Map of name -> ID
        "results": results
    }


@app.get("/notebooklm/notebooks")
def notebooklm_get_notebooks():
    """
    Get list of available NotebookLM notebooks.
    """
    notebooks = []
    for name, notebook_id in NOTEBOOKLM_NOTEBOOK_IDS.items():
        notebooks.append({
            "name": name,
            "id": notebook_id
        })
    
    return {
        "notebooks": notebooks
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
# Bucketeer API
# ============================================================================

class BucketeerRequest(BaseModel):
    content: str
    source_name: Optional[str] = None
    source_type: Optional[str] = None
    content_type: Optional[str] = None
    url: Optional[str] = None


@app.post("/bucketeer/add-content")
def bucketeer_add_content(request: BucketeerRequest):
    """
    Add content to Bucketeer. Bucketeer will automatically classify the content
    into appropriate buckets using vector embeddings.
    """
    import requests
    import traceback
    import json
    
    if not request.content or not request.content.strip():
        raise HTTPException(status_code=400, detail="Content cannot be empty")
    
    try:
        print(f"[Bucketeer] Adding content to Bucketeer...")
        print(f"[Bucketeer] Content length: {len(request.content)} chars")
        print(f"[Bucketeer] Source: {request.source_name}")
        print(f"[Bucketeer] Type: {request.source_type}")
        
        # Ensure content is a string (not a dict/array)
        if not isinstance(request.content, str):
            print(f"[Bucketeer] Warning: Content is not a string, serializing to JSON...")
            request.content = json.dumps(request.content, ensure_ascii=False)
        
        # Clean Unicode surrogate characters (emojis) before sending to Bucketeer
        cleaned_content = clean_unicode_for_bucketeer(request.content)
        print(f"[Bucketeer] Cleaned content length: {len(cleaned_content)} chars")
        
        headers = {
            "Authorization": f"Bearer {BUCKETEER_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Bucketeer API expects content and published_on fields
        # Get current date/time in ISO format (e.g., "2025-12-07T10:30:00")
        published_on = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        
        payload = {
            "content": str(cleaned_content),
            "published_on": published_on
        }
        
        # Validate payload can be serialized to JSON
        try:
            json.dumps(payload)
        except (TypeError, ValueError) as json_error:
            print(f"[Bucketeer] ❌ JSON serialization error: {json_error}")
            raise HTTPException(
                status_code=400,
                detail=f"Content cannot be serialized to JSON: {str(json_error)}"
            )
        
        # Determine the full endpoint URL
        # Base URL: https://bucketeer.adgo-infra.com/
        # Endpoint: /api/v1/content/
        # Full URL: https://bucketeer.adgo-infra.com/api/v1/content/
        if BUCKETEER_BASE_URL.endswith('/'):
            endpoint_url = f"{BUCKETEER_BASE_URL}api/v1/content/"
        else:
            endpoint_url = f"{BUCKETEER_BASE_URL}/api/v1/content/"
        
        print(f"[Bucketeer] Endpoint: {endpoint_url}")
        print(f"[Bucketeer] Base URL: {BUCKETEER_BASE_URL}")
        print(f"[Bucketeer] Content length: {len(request.content)} chars")
        print(f"[Bucketeer] Payload preview (first 500 chars): {request.content[:500]}...")
        print(f"[Bucketeer] Payload preview (last 200 chars): ...{request.content[-200:]}")
        
        # Retry logic with exponential backoff for timeout/connection errors
        max_retries = 3
        retry_delay = 2  # seconds
        response = None
        last_error = None
        
        for attempt in range(max_retries):
            try:
                print(f"[Bucketeer] Attempt {attempt + 1}/{max_retries}...")
                response = requests.post(
                    endpoint_url,
                    json=payload,
                    headers=headers,
                    timeout=120.0  # Increased timeout to 120 seconds
                )
                break  # Success, exit retry loop
            except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError) as timeout_error:
                last_error = timeout_error
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)  # Exponential backoff: 2s, 4s, 8s
                    print(f"[Bucketeer] ⚠️ Timeout/Connection error (attempt {attempt + 1}/{max_retries}): {str(timeout_error)}")
                    print(f"[Bucketeer] Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    print(f"[Bucketeer] ❌ All retry attempts failed")
                    raise HTTPException(
                        status_code=504,
                        detail=f"Bucketeer API timeout after {max_retries} attempts: {str(timeout_error)}"
                    )
        
        if response is None:
            raise HTTPException(
                status_code=504,
                detail=f"Bucketeer API timeout: {str(last_error) if last_error else 'Unknown error'}"
            )
        
        print(f"[Bucketeer] Response status: {response.status_code}")
        print(f"[Bucketeer] Response headers: {dict(response.headers)}")
        
        if response.status_code == 201:
            try:
                result = response.json()
                print(f"[Bucketeer] ✅ Success! Content added with ID: {result.get('id', 'unknown')}")
                print(f"[Bucketeer] Buckets assigned: {result.get('buckets', [])}")
                
                return {
                    "success": True,
                    "message": f"Content successfully added to Bucketeer",
                    "content_id": result.get("id"),
                    "buckets": result.get("buckets", [])
                }
            except ValueError as json_error:
                print(f"[Bucketeer] ⚠️ Response is not JSON: {response.text[:500]}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Bucketeer returned non-JSON response: {response.text[:200]}"
                )
        else:
            error_text = response.text
            print(f"[Bucketeer] ❌ Error: {response.status_code}")
            print(f"[Bucketeer] Response: {error_text[:500]}")
            raise HTTPException(
                status_code=500,
                detail=f"Bucketeer API error ({response.status_code}): {error_text[:200]}"
            )
            
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        print(f"[Bucketeer] ❌ HTTP error: {error_msg}")
        print(f"[Bucketeer] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to connect to Bucketeer: {error_msg}")
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        print(f"[Bucketeer] ❌ Unexpected error: {error_msg}")
        print(f"[Bucketeer] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {error_msg}")


# ============================================================================
# Scheduled Agents API
# ============================================================================

import json
import uuid
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

# Agents file path - use absolute path to ensure it's found
AGENTS_FILE = os.path.join(os.path.dirname(__file__), "agents.json")
# Scheduler timezone: Asia/Bangkok (Thailand Time, UTC+7)
bangkok_tz = pytz.timezone('Asia/Bangkok')
scheduler = BackgroundScheduler(timezone=bangkok_tz)
scheduler.start()
print(f"[Scheduler] ✅ Started with timezone: Asia/Bangkok (UTC+7)")
print(f"[Scheduler] Current time: {datetime.now(bangkok_tz).strftime('%Y-%m-%d %H:%M:%S %Z')}")

# Agent execution lock and queue to prevent concurrent executions
import threading
import queue
agent_execution_lock = threading.Lock()
agent_execution_queue = queue.Queue()
currently_running_agents = set()  # Track which agents are currently running

def load_agents():
    """Load agents from JSON file."""
    print(f"[Agents] Loading agents from: {AGENTS_FILE}")
    print(f"[Agents] File exists: {os.path.exists(AGENTS_FILE)}")
    if os.path.exists(AGENTS_FILE):
        try:
            with open(AGENTS_FILE, 'r') as f:
                data = json.load(f)
                agents = data.get('agents', [])
                print(f"[Agents] ✅ Loaded {len(agents)} agent(s) from file")
                return agents
        except Exception as e:
            print(f"[Agents] ❌ Error loading agents: {e}")
            import traceback
            traceback.print_exc()
            return []
    else:
        print(f"[Agents] ⚠️ Agents file not found at: {AGENTS_FILE}")
        print(f"[Agents] Current working directory: {os.getcwd()}")
        print(f"[Agents] __file__ directory: {os.path.dirname(__file__)}")
    return []

def save_agents(agents):
    """Save agents to JSON file."""
    try:
        with open(AGENTS_FILE, 'w') as f:
            json.dump({'agents': agents}, f, indent=2)
    except Exception as e:
        print(f"[Agents] Error saving agents: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save agents: {str(e)}")

def calculate_next_run(schedule_type: str, schedule_time: str, last_run: Optional[str] = None):
    """Calculate next run time based on schedule."""
    # Using Asia/Bangkok timezone (Thailand Time, UTC+7)
    now = datetime.now(pytz.timezone('Asia/Bangkok'))
    
    if schedule_type == "daily":
        # schedule_time format: "HH:MM"
        hour, minute = map(int, schedule_time.split(':'))
        next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # If time has passed today, schedule for tomorrow
        if next_run <= now:
            next_run += timedelta(days=1)
        
        return next_run.isoformat()
    
    elif schedule_type == "weekly":
        # schedule_time format: "day_of_week" (0=Monday, 6=Sunday)
        target_day = int(schedule_time)
        days_ahead = target_day - now.weekday()
        
        if days_ahead <= 0:  # Target day already passed this week
            days_ahead += 7
        
        next_run = now + timedelta(days=days_ahead)
        next_run = next_run.replace(hour=9, minute=0, second=0, microsecond=0)  # Default to 9 AM
        
        return next_run.isoformat()
    
    return None

def format_twitter_results_for_bucketeer(data: dict, posts: list) -> str:
    """Format Twitter analysis results for Bucketeer."""
    timeframe = data.get('timeframe', 1)
    timeframe_str = f"{timeframe} {'week' if timeframe == 1 else 'weeks'}"
    
    md = f"# Twitter Analysis Report\n\n"
    md += f"**Generated:** {datetime.now().isoformat()}\n\n"
    md += f"**Topic:** {data.get('topic', 'N/A')}\n\n"
    md += f"**Timeframe:** {timeframe_str}\n\n"
    md += f"**Accounts Analyzed:** {len(data.get('handles', []))}\n\n"
    md += f"**Total Posts Found:** {len(posts)}\n\n"
    md += f"---\n\n"
    
    # Sort posts by views
    sorted_posts = sorted(posts, key=lambda x: x.get('views', 0), reverse=True)
    
    for i, post in enumerate(sorted_posts[:50], 1):  # Limit to top 50 posts
        md += f"### {i}. @{post.get('author', 'unknown')}\n\n"
        md += f"**URL:** {post.get('url', 'N/A')}\n\n"
        if post.get('text'):
            md += f"**Content:**\n> {post.get('text', '')[:500]}\n\n"
        
        stats = []
        if post.get('views'): stats.append(f"{post['views']:,} views")
        if post.get('likes'): stats.append(f"{post['likes']:,} likes")
        if post.get('retweets'): stats.append(f"{post['retweets']:,} retweets")
        if stats:
            md += f"**Stats:** {' | '.join(stats)}\n\n"
        md += f"---\n\n"
    
    return md

def format_reddit_results_for_bucketeer(data: dict, posts: list) -> str:
    """Format Reddit analysis results for Bucketeer."""
    md = f"# Reddit Analysis Report: r/{data.get('subreddit', 'unknown')}\n\n"
    md += f"**Generated:** {datetime.now().isoformat()}\n\n"
    md += f"**Subreddit:** r/{data.get('subreddit', 'unknown')}\n\n"
    md += f"**Posts Analyzed:** {len(posts)}\n\n"
    md += f"---\n\n"
    
    sorted_posts = sorted(posts, key=lambda x: x.get('score', 0), reverse=True)
    
    for i, post in enumerate(sorted_posts[:30], 1):  # Limit to top 30 posts
        md += f"### {i}. {post.get('title', 'No title')}\n\n"
        md += f"**URL:** {post.get('url', 'N/A')}\n\n"
        md += f"**Author:** u/{post.get('author', '[deleted]')}\n\n"
        md += f"**Score:** {post.get('score', 0):,} | **Comments:** {post.get('num_comments', 0):,}\n\n"
        if post.get('selftext'):
            md += f"**Content:**\n> {post.get('selftext', '')[:500]}\n\n"
        md += f"---\n\n"
    
    return md

def format_polymarket_results_for_bucketeer(keyword: str, results: list) -> str:
    """Format Polymarket search results for Bucketeer."""
    md = f"# Polymarket Search Results\n\n"
    md += f"**Generated:** {datetime.now().isoformat()}\n\n"
    md += f"**Search Keyword:** {keyword}\n\n"
    md += f"**Markets Found:** {len(results)}\n\n"
    md += f"---\n\n"
    
    for i, market in enumerate(results[:20], 1):  # Limit to top 20 markets
        md += f"## {i}. {market.get('title', 'Unknown')}\n\n"
        md += f"**Slug:** `{market.get('slug', 'N/A')}`\n\n"
        md += f"**Volume:** ${market.get('volume', 0):,}\n\n"
        md += f"**Liquidity:** ${market.get('liquidity', 0):,}\n\n"
        md += f"**URL:** {market.get('url', 'N/A')}\n\n"
        if market.get('description'):
            md += f"**Description:**\n{market.get('description', '')[:500]}\n\n"
        md += f"---\n\n"
    
    return md

def execute_agent(agent: dict):
    """Execute an agent's query and send results to Bucketeer.
    
    Uses a lock to prevent concurrent executions and queues agents if one is already running.
    """
    agent_id = agent.get('id')
    agent_name = agent.get('name')
    
    # Check if this agent is already running
    if agent_id in currently_running_agents:
        print(f"[Agent] ⚠️ {agent_name} (ID: {agent_id}) is already running, skipping duplicate execution")
        return
    
    # Try to acquire lock, if busy, queue the agent
    if not agent_execution_lock.acquire(blocking=False):
        print(f"[Agent] ⏳ Another agent is running, queuing {agent_name} (ID: {agent_id})")
        agent_execution_queue.put(agent)
        return
    
    try:
        # Mark agent as running
        currently_running_agents.add(agent_id)
        
        # Execute the agent
        _execute_agent_internal(agent)
        
    finally:
        # Always release lock and remove from running set
        currently_running_agents.discard(agent_id)
        agent_execution_lock.release()
        
        # Process next agent in queue if any
        if not agent_execution_queue.empty():
            try:
                next_agent = agent_execution_queue.get_nowait()
                print(f"[Agent] 🔄 Processing queued agent: {next_agent.get('name')} (ID: {next_agent.get('id')})")
                # Run in a new thread to avoid blocking
                threading.Thread(target=execute_agent, args=[next_agent], daemon=True).start()
            except queue.Empty:
                pass

def _execute_agent_internal(agent: dict):
    """Internal function that actually executes the agent logic."""
    agent_id = agent.get('id')
    agent_name = agent.get('name')
    source_type = agent.get('source_type')
    query_params = agent.get('query_params', {})
    
    print(f"")
    print(f"=" * 60)
    print(f"[Agent] EXECUTING: {agent_name} (ID: {agent_id})")
    print(f"=" * 60)
    
    try:
        results_content = ""
        source_name = f"{agent_name} - {datetime.now().strftime('%Y-%m-%d')}"
        
        if source_type == "twitter":
            # Call Twitter analysis
            request = TwitterAnalysisRequest(**query_params)
            result = twitter_analyze(request)
            
            # Format for Bucketeer
            results_content = format_twitter_results_for_bucketeer(
                {'topic': query_params.get('topic'), 'timeframe': query_params.get('timeframe'), 'handles': query_params.get('handles')},
                result.get('posts', [])
            )
            source_type_name = "twitter"
            
        elif source_type == "reddit":
            # Call Reddit analysis
            request = RedditAnalysisRequest(**query_params)
            result = reddit_analyze(request)
            
            # Format for Bucketeer
            results_content = format_reddit_results_for_bucketeer(
                {'subreddit': query_params.get('subreddit')},
                result.get('posts', [])
            )
            source_type_name = "reddit"
            
        elif source_type == "polymarket":
            # Call Polymarket search
            keyword = query_params.get('keyword', '')
            results = search_markets(keyword)
            
            # Extract events list from results dictionary
            events = results.get('events', []) if isinstance(results, dict) else results
            
            # Format for Bucketeer
            results_content = format_polymarket_results_for_bucketeer(keyword, events)
            source_type_name = "polymarket"
        
        else:
            raise ValueError(f"Unknown source type: {source_type}")
        
        # Send to Bucketeer
        print(f"[Agent] Sending results to Bucketeer...")
        bucketeer_request = BucketeerRequest(
            content=results_content,
            source_name=source_name,
            source_type=source_type_name,
            content_type="text"
        )
        
        bucketeer_result = bucketeer_add_content(bucketeer_request)
        
        # Update agent last_run
        agents = load_agents()
        for a in agents:
            if a['id'] == agent_id:
                a['last_run'] = datetime.now().isoformat()
                a['next_run'] = calculate_next_run(
                    a['schedule'],
                    a['schedule_time'],
                    a['last_run']
                )
                save_agents(agents)
                break
        
        print(f"[Agent] ✅ {agent_name} completed successfully")
        print(f"[Agent] Bucketeer ID: {bucketeer_result.get('content_id', 'unknown')}")
        
    except Exception as e:
        print(f"[Agent] ❌ Error executing {agent_name}: {str(e)}")
        import traceback
        traceback.print_exc()

class AgentCreateRequest(BaseModel):
    name: str
    source_type: str  # "twitter", "reddit", "polymarket"
    query_params: dict
    schedule: str  # "daily" or "weekly"
    schedule_time: str  # "HH:MM" for daily, "0-6" for weekly (0=Monday)

class AgentUpdateRequest(BaseModel):
    name: Optional[str] = None
    schedule: Optional[str] = None
    schedule_time: Optional[str] = None
    status: Optional[str] = None  # "active" or "paused"

@app.post("/agents/create")
def create_agent(request: AgentCreateRequest):
    """Create a new scheduled agent."""
    agents = load_agents()
    
    agent_id = str(uuid.uuid4())
    next_run = calculate_next_run(request.schedule, request.schedule_time)
    
    agent = {
        "id": agent_id,
        "name": request.name,
        "source_type": request.source_type,
        "query_params": request.query_params,
        "schedule": request.schedule,
        "schedule_time": request.schedule_time,
        "status": "active",
        "next_run": next_run,
        "last_run": None,
        "created_at": datetime.now().isoformat()
    }
    
    agents.append(agent)
    save_agents(agents)
    
    # Schedule the job
    if request.schedule == "daily":
        hour, minute = map(int, request.schedule_time.split(':'))
        scheduler.add_job(
            execute_agent,
            trigger=CronTrigger(hour=hour, minute=minute, timezone=bangkok_tz),
            id=agent_id,
            args=[agent],
            replace_existing=True
        )
    elif request.schedule == "weekly":
        day_of_week = int(request.schedule_time)
        scheduler.add_job(
            execute_agent,
            trigger=CronTrigger(day_of_week=day_of_week, hour=9, minute=0, timezone=bangkok_tz),
            id=agent_id,
            args=[agent],
            replace_existing=True
        )
    
    return {
        "success": True,
        "agent_id": agent_id,
        "next_run": next_run,
        "message": f"Agent '{request.name}' created successfully"
    }

@app.get("/agents")
def list_agents():
    """List all scheduled agents."""
    agents = load_agents()
    return {"agents": agents}

@app.get("/agents/{agent_id}")
def get_agent(agent_id: str):
    """Get a specific agent by ID."""
    agents = load_agents()
    agent = next((a for a in agents if a['id'] == agent_id), None)
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return agent

@app.put("/agents/{agent_id}")
def update_agent(agent_id: str, request: AgentUpdateRequest):
    """Update an agent."""
    agents = load_agents()
    agent = next((a for a in agents if a['id'] == agent_id), None)
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Update fields
    if request.name:
        agent['name'] = request.name
    if request.schedule:
        agent['schedule'] = request.schedule
    if request.schedule_time:
        agent['schedule_time'] = request.schedule_time
    if request.status:
        agent['status'] = request.status
    
    # Recalculate next_run if schedule changed
    if request.schedule or request.schedule_time:
        agent['next_run'] = calculate_next_run(agent['schedule'], agent['schedule_time'], agent.get('last_run'))
    
    # Update scheduler job
    try:
        scheduler.remove_job(agent_id)
    except:
        pass
    
    if agent['status'] == 'active':
        if agent['schedule'] == "daily":
            hour, minute = map(int, agent['schedule_time'].split(':'))
            scheduler.add_job(
                execute_agent,
                trigger=CronTrigger(hour=hour, minute=minute, timezone=bangkok_tz),
                id=agent_id,
                args=[agent],
                replace_existing=True
            )
        elif agent['schedule'] == "weekly":
            day_of_week = int(agent['schedule_time'])
            scheduler.add_job(
                execute_agent,
                trigger=CronTrigger(day_of_week=day_of_week, hour=9, minute=0, timezone=bangkok_tz),
                id=agent_id,
                args=[agent],
                replace_existing=True
            )
    
    save_agents(agents)
    
    return {"success": True, "agent": agent}

@app.delete("/agents/{agent_id}")
def delete_agent(agent_id: str):
    """Delete an agent."""
    agents = load_agents()
    agent = next((a for a in agents if a['id'] == agent_id), None)
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Remove from scheduler
    try:
        scheduler.remove_job(agent_id)
    except:
        pass
    
    agents = [a for a in agents if a['id'] != agent_id]
    save_agents(agents)
    
    return {"success": True, "message": "Agent deleted successfully"}

@app.post("/agents/{agent_id}/run")
def run_agent_now(agent_id: str):
    """Manually trigger an agent run."""
    agents = load_agents()
    agent = next((a for a in agents if a['id'] == agent_id), None)
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent_name = agent.get('name', 'Unknown')
    
    # Check if agent is already running
    if agent_id in currently_running_agents:
        return {
            "success": False,
            "message": f"Agent '{agent_name}' is already running",
            "status": "running",
            "agent_id": agent_id
        }
    
    # Check if another agent is running (will be queued)
    if not agent_execution_lock.acquire(blocking=False):
        # Another agent is running, this one will be queued
        thread = threading.Thread(target=execute_agent, args=[agent], daemon=True)
        thread.start()
        return {
            "success": True,
            "message": f"Agent '{agent_name}' queued for execution (another agent is running)",
            "status": "queued",
            "agent_id": agent_id
        }
    else:
        # Lock acquired, can run immediately
        agent_execution_lock.release()
        thread = threading.Thread(target=execute_agent, args=[agent], daemon=True)
        thread.start()
        return {
            "success": True,
            "message": f"Agent '{agent_name}' execution started",
            "status": "started",
            "agent_id": agent_id
        }

# Load existing agents and schedule them on startup
def initialize_agents():
    """Load and schedule all active agents on startup."""
    agents = load_agents()
    for agent in agents:
        if agent.get('status') == 'active':
            try:
                if agent['schedule'] == "daily":
                    hour, minute = map(int, agent['schedule_time'].split(':'))
                    scheduler.add_job(
                        execute_agent,
                        trigger=CronTrigger(hour=hour, minute=minute, timezone=bangkok_tz),
                        id=agent['id'],
                        args=[agent],
                        replace_existing=True
                    )
                    print(f"[Agents] ✅ Scheduled daily job for {agent['name']} at {hour:02d}:{minute:02d} Bangkok time")
                elif agent['schedule'] == "weekly":
                    day_of_week = int(agent['schedule_time'])
                    scheduler.add_job(
                        execute_agent,
                        trigger=CronTrigger(day_of_week=day_of_week, hour=9, minute=0, timezone=bangkok_tz),
                        id=agent['id'],
                        args=[agent],
                        replace_existing=True
                    )
                    print(f"[Agents] ✅ Scheduled weekly job for {agent['name']} on day {day_of_week} at 09:00 Bangkok time")
                print(f"[Agents] Scheduled agent: {agent['name']} (ID: {agent['id']})")
            except Exception as e:
                print(f"[Agents] Error scheduling agent {agent['name']}: {e}")

# Initialize agents on startup
try:
    initialize_agents()
    print("[App] ✅ Agents initialized successfully")
except Exception as e:
    print(f"[App] ⚠️ Warning: Error initializing agents: {e}")
    print("[App] Continuing without scheduled agents...")


# ============================================================================
# Run with uvicorn
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)



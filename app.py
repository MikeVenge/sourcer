"""
FastAPI Application for Sourcer
Deploy to Railway or run locally with: uvicorn app:app --reload
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
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


# ============================================================================
# Run with uvicorn
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)


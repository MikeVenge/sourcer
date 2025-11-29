"""
Vercel Serverless Function for Polymarket API
Endpoint: /api/polymarket

Query Parameters:
  - search: Search markets by keyword
  - slug: Fetch event by slug
  - tag: Fetch markets by tag ID
  - format: json (default) or text
"""

from http.server import BaseHTTPRequestHandler
import json
import sys
import os

# Add lib to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

from polymarket_reader import (
    search_markets,
    fetch_event_by_slug,
    fetch_markets_by_tag,
    format_search_results,
    format_event
)


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # Parse query parameters
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            
            search = params.get('search', [None])[0]
            slug = params.get('slug', [None])[0]
            tag = params.get('tag', [None])[0]
            output_format = params.get('format', ['json'])[0]
            
            result = None
            formatted = ""
            
            if search:
                result = search_markets(search)
                formatted = format_search_results(result)
            elif slug:
                result = fetch_event_by_slug(slug)
                formatted = format_event(result)
            elif tag:
                result = fetch_markets_by_tag(int(tag))
                formatted = json.dumps(result, indent=2)
            else:
                # Return usage info
                result = {
                    "usage": {
                        "search": "/api/polymarket?search=bitcoin",
                        "slug": "/api/polymarket?slug=what-will-googl-hit-before-2026",
                        "tag": "/api/polymarket?tag=100381",
                        "format": "Add &format=text for formatted output"
                    }
                }
                formatted = json.dumps(result, indent=2)
            
            # Send response
            self.send_response(200)
            
            if output_format == 'text':
                self.send_header('Content-Type', 'text/plain')
                response = formatted
            else:
                self.send_header('Content-Type', 'application/json')
                response = json.dumps(result, indent=2)
            
            self.end_headers()
            self.wfile.write(response.encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            error_response = json.dumps({"error": str(e)})
            self.wfile.write(error_response.encode())



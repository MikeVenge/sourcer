"""
Vercel Serverless Function for Twitter/X Analysis API
Endpoint: /api/twitter

Query Parameters:
  - accounts: Comma-separated Twitter handles (e.g., @elonmusk,@sama)
  - topic: Search topic (default: "technology")
  - timeframe: How far back to look (default: "7 days")
  - post_count: Max posts per account (default: 10)
"""

from http.server import BaseHTTPRequestHandler
import json
import sys
import os

# Add lib to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

from twitter_reader import run_cot_v2, extract_x_urls, fetch_x_post_content


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # Parse query parameters
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            
            accounts_str = params.get('accounts', [None])[0]
            topic = params.get('topic', ['technology'])[0]
            timeframe = params.get('timeframe', ['7 days'])[0]
            post_count = int(params.get('post_count', ['10'])[0])
            
            if not accounts_str:
                # Return usage info
                result = {
                    "usage": {
                        "endpoint": "/api/twitter",
                        "params": {
                            "accounts": "Required. Comma-separated Twitter handles (e.g., @elonmusk,@sama)",
                            "topic": "Optional. Search topic (default: technology)",
                            "timeframe": "Optional. How far back (default: 7 days)",
                            "post_count": "Optional. Max posts (default: 10)"
                        },
                        "example": "/api/twitter?accounts=@elonmusk,@sama&topic=AI&timeframe=3 days&post_count=5"
                    }
                }
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(result, indent=2).encode())
                return
            
            # Parse accounts
            accounts = [a.strip() for a in accounts_str.split(',')]
            
            # Note: This requires the FinChat COT API session ID
            # For now, return a placeholder response
            result = {
                "status": "pending",
                "message": "Twitter analysis requires FinChat COT API configuration",
                "params": {
                    "accounts": accounts,
                    "topic": topic,
                    "timeframe": timeframe,
                    "post_count": post_count
                }
            }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result, indent=2).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            error_response = json.dumps({"error": str(e)})
            self.wfile.write(error_response.encode())



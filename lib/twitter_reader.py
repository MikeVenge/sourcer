#!/usr/bin/env python3
"""
Script to run FinChat COT API v2 for Twitter analysis.

Usage:
    python run_cot.py --accounts "@user1 @user2" --topic "AI startups" --timeframe "7 days" --post_count 100
"""

import requests
import time
import sys
import argparse
import re
import json


def run_cot_v2(session_id: str, accounts: list, topic: str, timeframe: str, post_count: int,
               base_url: str = 'https://finchat-api.adgo.io', timeout: int = 600) -> str:
    """
    Execute COT using v2 API with pre-configured session.
    
    Args:
        session_id: The pre-configured COT session ID
        accounts: List of Twitter handles to analyze
        topic: Search string of what you are looking for
        timeframe: How far back to look back
        post_count: Max number of posts to retrieve
        base_url: API base URL
        timeout: Maximum time to wait for results (seconds)
    
    Returns:
        The processed result content
    """
    headers = {'Content-Type': 'application/json'}
    
    # Build the payload with the correct parameters
    payload = {
        'accounts': accounts,
        'topic': topic,
        'timeframe': timeframe,
        'post_count': post_count
    }
    
    # Step 1: Execute COT
    print(f"Executing COT with session: {session_id}")
    print(f"Parameters:")
    print(f"  accounts: {accounts}")
    print(f"  topic: {topic}")
    print(f"  timeframe: {timeframe}")
    print(f"  post_count: {post_count}")
    
    response = requests.post(
        f"{base_url}/api/v2/sessions/run-cot/{session_id}/",
        json=payload,
        headers=headers
    )
    response.raise_for_status()
    new_session_id = response.json()['id']
    print(f"New session created: {new_session_id}")
    
    # Step 2: Poll for results
    results_url = f"{base_url}/api/v2/sessions/{new_session_id}/results/"
    start_time = time.time()
    poll_interval = 10  # seconds
    
    print("Polling for results...")
    while time.time() - start_time < timeout:
        response = requests.get(results_url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        status = data.get('status', 'unknown')
        results = data.get('results', [])
        
        elapsed = int(time.time() - start_time)
        print(f"  [{elapsed}s] Status: {status}")
        
        # Check if completed
        if status == 'idle' and len(results) > 0:
            print(f"Completed after {elapsed} seconds")
            return results[0]['content']
        
        time.sleep(poll_interval)
    
    raise TimeoutError(f"COT execution timed out after {timeout} seconds")


def extract_x_urls(text: str) -> list:
    """
    Extract X/Twitter URLs from text.
    
    Args:
        text: Text containing X URLs
    
    Returns:
        List of X URLs
    """
    # Match x.com or twitter.com URLs
    pattern = r'https?://(?:x\.com|twitter\.com)/\w+/status/\d+'
    urls = re.findall(pattern, text)
    return urls


def fetch_x_post_content(url: str) -> dict:
    """
    Fetch the content of an X post by scraping page metadata.
    
    Args:
        url: The X post URL
    
    Returns:
        Dictionary with post content including author, text, and engagement stats
    """
    # Use fxtwitter.com which provides better metadata access
    # Convert x.com or twitter.com URL to api.fxtwitter.com
    if 'x.com' in url:
        fx_url = url.replace('x.com', 'api.fxtwitter.com')
    elif 'twitter.com' in url:
        fx_url = url.replace('twitter.com', 'api.fxtwitter.com')
    else:
        fx_url = url
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        # Try fxtwitter API first (provides JSON response)
        response = requests.get(fx_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            tweet = data.get('tweet', {})
            author = tweet.get('author', {})
            
            return {
                'url': url,
                'author': author.get('screen_name', 'Unknown'),
                'author_name': author.get('name', 'Unknown'),
                'text': tweet.get('text', ''),
                'created_at': tweet.get('created_at', ''),
                'likes': tweet.get('likes', 0),
                'retweets': tweet.get('retweets', 0),
                'replies': tweet.get('replies', 0),
                'views': tweet.get('views', 0),
                'media': tweet.get('media', {}).get('all', []),
                'quoted_tweet': tweet.get('quote', None)
            }
        
        # Fallback: try to scrape meta tags from the original URL
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        html = response.text
        
        # Extract from meta tags
        result = {'url': url}
        
        # Try to get content from og:description or twitter:description
        og_desc_match = re.search(r'<meta\s+(?:property|name)=["\']og:description["\']\s+content=["\']([^"\']+)["\']', html)
        if og_desc_match:
            result['text'] = og_desc_match.group(1)
        
        # Try to get author from title (format: "Author on X: ...")
        title_match = re.search(r'<title>([^<]+)</title>', html)
        if title_match:
            title = title_match.group(1)
            result['title'] = title
            # Parse author from title
            author_match = re.match(r'^(.+?)\s+on\s+X:', title)
            if author_match:
                result['author_name'] = author_match.group(1)
            # Extract tweet text from title if og:description not found
            if 'text' not in result:
                text_match = re.search(r'on X: ["\'](.+)["\']', title)
                if text_match:
                    result['text'] = text_match.group(1)
        
        return result
        
    except requests.RequestException as e:
        return {'url': url, 'error': str(e)}
    except Exception as e:
        return {'url': url, 'error': str(e)}


def fetch_all_posts(urls: list) -> list:
    """
    Fetch content for all X post URLs.
    
    Args:
        urls: List of X post URLs
    
    Returns:
        List of dictionaries with post content
    """
    results = []
    for i, url in enumerate(urls, 1):
        print(f"\nFetching post {i}/{len(urls)}: {url}")
        result = fetch_x_post_content(url)
        results.append(result)
        if 'error' not in result:
            print(f"  ✓ Fetched successfully")
        else:
            print(f"  ✗ Error: {result.get('error', 'Unknown error')}")
    
    return results


def format_post_content(post: dict) -> str:
    """
    Format post content for display.
    
    Args:
        post: Dictionary with post data
    
    Returns:
        Formatted string
    """
    if 'error' in post:
        return f"Error: {post['error']}"
    
    lines = []
    
    # Author info
    author_name = post.get('author_name', '')
    author_handle = post.get('author', '')
    if author_name and author_handle:
        lines.append(f"Author: {author_name} (@{author_handle})")
    elif author_name:
        lines.append(f"Author: {author_name}")
    
    # Tweet text
    text = post.get('text', post.get('title', ''))
    if text:
        lines.append(f"\nContent:\n{text}")
    
    # Engagement stats
    stats = []
    if post.get('views'):
        stats.append(f"{post['views']:,} views")
    if post.get('likes'):
        stats.append(f"{post['likes']:,} likes")
    if post.get('retweets'):
        stats.append(f"{post['retweets']:,} retweets")
    if post.get('replies'):
        stats.append(f"{post['replies']:,} replies")
    
    if stats:
        lines.append(f"\nStats: {' | '.join(stats)}")
    
    # Created at
    if post.get('created_at'):
        lines.append(f"Posted: {post['created_at']}")
    
    # Quoted tweet
    if post.get('quoted_tweet'):
        qt = post['quoted_tweet']
        qt_author = qt.get('author', {})
        lines.append(f"\n📎 Quoted Tweet from @{qt_author.get('screen_name', 'unknown')}:")
        lines.append(f"   {qt.get('text', '')[:200]}...")
    
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='Run FinChat COT API v2 for Twitter analysis'
    )
    parser.add_argument(
        '--accounts',
        type=str,
        required=True,
        help='Space-separated list of Twitter handles (e.g., "@user1 @user2")'
    )
    parser.add_argument(
        '--topic',
        type=str,
        required=True,
        help='Search string of what you are looking for'
    )
    parser.add_argument(
        '--timeframe',
        type=str,
        required=True,
        help='How far back to look back (e.g., "7 days", "1 month")'
    )
    parser.add_argument(
        '--post_count',
        type=int,
        required=True,
        help='Max number of posts to retrieve'
    )
    parser.add_argument(
        '--session-id',
        type=str,
        default='692525b7fcc4aae81ac5eaf8',
        help='COT session ID (default: 692525b7fcc4aae81ac5eaf8)'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=600,
        help='Timeout in seconds (default: 600)'
    )
    parser.add_argument(
        '--base-url',
        type=str,
        default='https://finchat-api.adgo.io',
        help='API base URL (default: https://finchat-api.adgo.io)'
    )
    parser.add_argument(
        '--fetch-posts',
        action='store_true',
        help='Fetch full content of each X post found in the results'
    )
    
    args = parser.parse_args()
    
    # Parse accounts from space-separated string to list
    accounts_list = args.accounts.split()
    
    if not accounts_list:
        print("Error: At least one account is required", file=sys.stderr)
        sys.exit(1)
    
    try:
        result = run_cot_v2(
            session_id=args.session_id,
            accounts=accounts_list,
            topic=args.topic,
            timeframe=args.timeframe,
            post_count=args.post_count,
            base_url=args.base_url,
            timeout=args.timeout
        )
        print("\n" + "="*50)
        print("RESULT:")
        print("="*50)
        print(result)
        
        # If --fetch-posts is specified, extract URLs and fetch post content
        if args.fetch_posts:
            urls = extract_x_urls(result)
            if urls:
                print("\n" + "="*50)
                print(f"FETCHING {len(urls)} X POSTS:")
                print("="*50)
                
                post_contents = fetch_all_posts(urls)
                
                print("\n" + "="*50)
                print("POST CONTENTS:")
                print("="*50)
                for i, post in enumerate(post_contents, 1):
                    print(f"\n{'─'*50}")
                    print(f"Post {i}: {post['url']}")
                    print('─'*50)
                    print(format_post_content(post))
            else:
                print("\nNo X URLs found in the result.")
    except requests.HTTPError as e:
        print(f"HTTP Error: {e}", file=sys.stderr)
        print(f"Response: {e.response.text if e.response else 'No response'}", file=sys.stderr)
        sys.exit(1)
    except TimeoutError as e:
        print(f"Timeout: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

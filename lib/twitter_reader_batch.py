#!/usr/bin/env python3
"""
Batch script to run COT for multiple Twitter handles and consolidate results.
"""

import sys
import time
from datetime import datetime
from run_cot import run_cot_v2, extract_x_urls, fetch_all_posts, format_post_content

# Twitter handles to process
HANDLES = [
    "@acapitallp",
    "@adamdangelo",
    "@alexisohanian",
    "@altcap",
    "@bhorowitz",
    "@bgurley",
    "@chetanp",
    "@chamath",
    "@contrary_res",
    "@crossbordercap",
    "@davidsacks",
    "@deanmeyerrr",
    "@eladgil",
    "@firstadapter",
    "@fredwilson",
    "@friedberg",
    "@garrytan",
    "@grahamduncannyc",
    "@harrystebbings",
    "@jia_seed",
    "@jonsakoda",
    "@jtlondsdale",
    "@kirstenagreen",
    "@palmerlucky",
    "@patrickc",
    "@paulg",
    "@pmarca",
    "@reidhoffman",
]

# COT parameters
SESSION_ID = "692525b7fcc4aae81ac5eaf8"
TOPIC = "venture investing, AI, technology, GPU, data centers"
TIMEFRAME = "5 days"
POST_COUNT = 10
BASE_URL = "https://finchat-api.adgo.io"
TIMEOUT = 600


def process_handle(handle: str) -> dict:
    """
    Process a single Twitter handle and return results.
    """
    print(f"\n{'='*60}")
    print(f"Processing: {handle}")
    print('='*60)
    
    try:
        # Run COT
        result = run_cot_v2(
            session_id=SESSION_ID,
            accounts=[handle],
            topic=TOPIC,
            timeframe=TIMEFRAME,
            post_count=POST_COUNT,
            base_url=BASE_URL,
            timeout=TIMEOUT
        )
        
        # Extract URLs and fetch posts
        urls = extract_x_urls(result)
        posts = []
        
        if urls:
            print(f"Found {len(urls)} posts, fetching content...")
            posts = fetch_all_posts(urls)
        else:
            print("No posts found for this handle.")
        
        return {
            'handle': handle,
            'cot_result': result,
            'urls': urls,
            'posts': posts,
            'error': None
        }
        
    except Exception as e:
        print(f"Error processing {handle}: {e}")
        return {
            'handle': handle,
            'cot_result': None,
            'urls': [],
            'posts': [],
            'error': str(e)
        }


def main():
    print("="*60)
    print("BATCH COT PROCESSING")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Topic: {TOPIC}")
    print(f"Timeframe: {TIMEFRAME}")
    print(f"Handles to process: {len(HANDLES)}")
    print("="*60)
    
    all_results = []
    all_posts = []
    
    for i, handle in enumerate(HANDLES, 1):
        print(f"\n[{i}/{len(HANDLES)}] Processing {handle}...")
        result = process_handle(handle)
        all_results.append(result)
        
        # Collect all posts
        if result['posts']:
            for post in result['posts']:
                post['source_handle'] = handle
                all_posts.append(post)
        
        # Small delay between requests to be respectful
        if i < len(HANDLES):
            time.sleep(2)
    
    # Generate consolidated report
    report_filename = f"consolidated_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    
    with open(report_filename, 'w') as f:
        f.write("# Consolidated Twitter/X Analysis Report\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**Topic:** {TOPIC}\n\n")
        f.write(f"**Timeframe:** {TIMEFRAME}\n\n")
        f.write(f"**Accounts Analyzed:** {len(HANDLES)}\n\n")
        f.write("---\n\n")
        
        # Summary statistics
        total_posts = len(all_posts)
        handles_with_posts = len([r for r in all_results if r['posts']])
        handles_with_errors = len([r for r in all_results if r['error']])
        
        f.write("## Summary\n\n")
        f.write(f"- **Total Posts Found:** {total_posts}\n")
        f.write(f"- **Accounts with Relevant Posts:** {handles_with_posts}\n")
        f.write(f"- **Accounts with No Posts:** {len(HANDLES) - handles_with_posts - handles_with_errors}\n")
        f.write(f"- **Errors:** {handles_with_errors}\n\n")
        f.write("---\n\n")
        
        # All posts sorted by engagement (views)
        f.write("## All Posts (Sorted by Views)\n\n")
        
        # Sort posts by views (descending)
        sorted_posts = sorted(
            [p for p in all_posts if 'error' not in p],
            key=lambda x: x.get('views', 0),
            reverse=True
        )
        
        for i, post in enumerate(sorted_posts, 1):
            f.write(f"### {i}. {post.get('author_name', 'Unknown')} (@{post.get('author', 'unknown')})\n\n")
            f.write(f"**URL:** {post.get('url', 'N/A')}\n\n")
            
            text = post.get('text', '')
            if text:
                f.write(f"**Content:**\n> {text}\n\n")
            
            # Stats
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
                f.write(f"**Stats:** {' | '.join(stats)}\n\n")
            
            if post.get('created_at'):
                f.write(f"**Posted:** {post['created_at']}\n\n")
            
            # Quoted tweet
            if post.get('quoted_tweet'):
                qt = post['quoted_tweet']
                qt_author = qt.get('author', {})
                f.write(f"**Quoted Tweet from @{qt_author.get('screen_name', 'unknown')}:**\n")
                f.write(f"> {qt.get('text', '')[:300]}...\n\n")
            
            f.write("---\n\n")
        
        # Results by handle
        f.write("## Results by Account\n\n")
        
        for result in all_results:
            handle = result['handle']
            f.write(f"### {handle}\n\n")
            
            if result['error']:
                f.write(f"**Error:** {result['error']}\n\n")
            elif not result['posts']:
                f.write("No relevant posts found in the timeframe.\n\n")
            else:
                f.write(f"**Posts Found:** {len(result['posts'])}\n\n")
                for post in result['posts']:
                    if 'error' not in post:
                        f.write(f"- [{post.get('text', 'No text')[:80]}...]({post.get('url', '')})\n")
                f.write("\n")
            
            f.write("---\n\n")
    
    print("\n" + "="*60)
    print("BATCH PROCESSING COMPLETE")
    print("="*60)
    print(f"Total handles processed: {len(HANDLES)}")
    print(f"Total posts found: {total_posts}")
    print(f"Report saved to: {report_filename}")
    print("="*60)
    
    # Also print to console
    print("\n\nTOP POSTS BY ENGAGEMENT:\n")
    for i, post in enumerate(sorted_posts[:10], 1):
        views = post.get('views', 0)
        author = post.get('author', 'unknown')
        text = post.get('text', '')[:100]
        print(f"{i}. @{author} ({views:,} views)")
        print(f"   {text}...")
        print()


if __name__ == '__main__':
    main()


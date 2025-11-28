#!/usr/bin/env python3
"""
Polymarket Reader - Fetch and analyze prediction markets from Polymarket.

Usage:
    python polymarket_reader.py --search "bitcoin"           # Search markets by keyword
    python polymarket_reader.py --slug "fed-decision"        # Fetch specific event by slug
    python polymarket_reader.py --tag 100381                 # Fetch markets by tag ID
    python polymarket_reader.py --list-tags                  # List all available tags
"""

import requests
import argparse
import sys
import json
from datetime import datetime


BASE_URL = "https://gamma-api.polymarket.com"


def search_markets(keyword: str, limit: int = 100, include_closed: bool = False) -> dict:
    """
    Search for markets by keyword using the public-search API endpoint.
    
    Args:
        keyword: Search term
        limit: Max events to return
        include_closed: Include closed markets
    
    Returns:
        Dictionary with matching events and tags
    """
    print(f"Searching for: '{keyword}'")
    
    # Use the public-search endpoint
    response = requests.get(
        f"{BASE_URL}/public-search",
        params={'q': keyword},
        timeout=30
    )
    response.raise_for_status()
    results = response.json()
    
    events = results.get('events', [])
    tags = results.get('tags', [])
    
    # Filter out closed events if requested
    if not include_closed:
        events = [e for e in events if not e.get('closed', False)]
    
    # Limit results
    events = events[:limit]
    
    print(f"  Found {len(events)} events, {len(tags)} tags")
    
    return {'events': events, 'tags': tags}


def fetch_event_by_slug(slug: str) -> dict:
    """
    Fetch a specific event by its slug.
    
    Args:
        slug: Event slug (from URL path)
    
    Returns:
        Event data dictionary
    """
    print(f"Fetching event: {slug}")
    
    response = requests.get(
        f"{BASE_URL}/events/slug/{slug}",
        timeout=30
    )
    response.raise_for_status()
    return response.json()


def fetch_market_by_slug(slug: str) -> dict:
    """
    Fetch a specific market by its slug.
    
    Args:
        slug: Market slug (from URL path)
    
    Returns:
        Market data dictionary
    """
    print(f"Fetching market: {slug}")
    
    response = requests.get(
        f"{BASE_URL}/markets/slug/{slug}",
        timeout=30
    )
    response.raise_for_status()
    return response.json()


def fetch_markets_by_tag(tag_id: int, limit: int = 50, closed: bool = False) -> list:
    """
    Fetch markets by tag ID.
    
    Args:
        tag_id: Tag ID to filter by
        limit: Max results per page
        closed: Include closed markets
    
    Returns:
        List of markets
    """
    print(f"Fetching markets with tag ID: {tag_id}")
    
    all_markets = []
    offset = 0
    
    while True:
        response = requests.get(
            f"{BASE_URL}/markets",
            params={
                'tag_id': tag_id,
                'limit': limit,
                'offset': offset,
                'closed': str(closed).lower()
            },
            timeout=30
        )
        response.raise_for_status()
        markets = response.json()
        
        if not markets:
            break
        
        all_markets.extend(markets)
        print(f"  Fetched {len(markets)} markets (total: {len(all_markets)})")
        
        if len(markets) < limit:
            break
        
        offset += limit
    
    return all_markets


def fetch_events_by_tag(tag_id: int, limit: int = 50, closed: bool = False) -> list:
    """
    Fetch events by tag ID.
    
    Args:
        tag_id: Tag ID to filter by
        limit: Max results per page
        closed: Include closed events
    
    Returns:
        List of events
    """
    print(f"Fetching events with tag ID: {tag_id}")
    
    all_events = []
    offset = 0
    
    while True:
        response = requests.get(
            f"{BASE_URL}/events",
            params={
                'tag_id': tag_id,
                'limit': limit,
                'offset': offset,
                'closed': str(closed).lower()
            },
            timeout=30
        )
        response.raise_for_status()
        events = response.json()
        
        if not events:
            break
        
        all_events.extend(events)
        print(f"  Fetched {len(events)} events (total: {len(all_events)})")
        
        if len(events) < limit:
            break
        
        offset += limit
    
    return all_events


def list_tags() -> list:
    """
    List all available tags.
    
    Returns:
        List of tags
    """
    print("Fetching available tags...")
    
    response = requests.get(
        f"{BASE_URL}/tags",
        timeout=30
    )
    response.raise_for_status()
    return response.json()


def format_search_results(results: dict) -> str:
    """Format search results for display."""
    lines = []
    
    # Events
    events = results.get('events', [])
    if events:
        lines.append(f"\n{'='*60}")
        lines.append(f"EVENTS ({len(events)} found)")
        lines.append('='*60)
        
        for i, event in enumerate(events, 1):
            lines.append(f"\n{i}. {event.get('title', 'N/A')}")
            lines.append(f"   Slug: {event.get('slug', 'N/A')}")
            lines.append(f"   URL: https://polymarket.com/event/{event.get('slug', '')}")
            
            if event.get('description'):
                desc = event['description'][:200] + '...' if len(event.get('description', '')) > 200 else event.get('description', '')
                lines.append(f"   Description: {desc}")
            
            if event.get('volume'):
                lines.append(f"   Volume: ${float(event.get('volume', 0)):,.2f}")
            
            if event.get('liquidity'):
                lines.append(f"   Liquidity: ${float(event.get('liquidity', 0)):,.2f}")
    
    # Tags
    tags = results.get('tags', [])
    if tags:
        lines.append(f"\n{'='*60}")
        lines.append(f"TAGS ({len(tags)} found)")
        lines.append('='*60)
        
        for tag in tags:
            lines.append(f"  - {tag.get('label', 'N/A')} (ID: {tag.get('id', 'N/A')})")
    
    if not events and not tags:
        lines.append("\nNo results found.")
    
    return '\n'.join(lines)


def format_event(event: dict) -> str:
    """Format a single event for display."""
    lines = []
    
    lines.append(f"\n{'='*60}")
    lines.append(f"EVENT: {event.get('title', 'N/A')}")
    lines.append('='*60)
    
    lines.append(f"\nSlug: {event.get('slug', 'N/A')}")
    lines.append(f"URL: https://polymarket.com/event/{event.get('slug', '')}")
    
    if event.get('description'):
        lines.append(f"\nDescription:\n{event.get('description', 'N/A')}")
    
    if event.get('volume'):
        lines.append(f"\nVolume: ${float(event.get('volume', 0)):,.2f}")
    
    if event.get('liquidity'):
        lines.append(f"Liquidity: ${float(event.get('liquidity', 0)):,.2f}")
    
    if event.get('startDate'):
        lines.append(f"Start Date: {event.get('startDate', 'N/A')}")
    
    if event.get('endDate'):
        lines.append(f"End Date: {event.get('endDate', 'N/A')}")
    
    # Markets within the event
    markets = event.get('markets', [])
    if markets:
        lines.append(f"\n{'-'*40}")
        lines.append(f"MARKETS ({len(markets)})")
        lines.append('-'*40)
        
        for i, market in enumerate(markets, 1):
            lines.append(f"\n  {i}. {market.get('question', market.get('groupItemTitle', 'N/A'))}")
            
            # Outcome prices
            outcome_prices = market.get('outcomePrices', '[]')
            if isinstance(outcome_prices, str):
                try:
                    outcome_prices = json.loads(outcome_prices)
                except:
                    outcome_prices = []
            
            outcomes = market.get('outcomes', '[]')
            if isinstance(outcomes, str):
                try:
                    outcomes = json.loads(outcomes)
                except:
                    outcomes = []
            
            if outcome_prices and outcomes:
                for j, (outcome, price) in enumerate(zip(outcomes, outcome_prices)):
                    try:
                        price_pct = float(price) * 100
                        lines.append(f"      {outcome}: {price_pct:.1f}%")
                    except:
                        lines.append(f"      {outcome}: {price}")
            
            if market.get('volume'):
                lines.append(f"      Volume: ${float(market.get('volume', 0)):,.2f}")
    
    return '\n'.join(lines)


def format_markets(markets: list) -> str:
    """Format markets list for display."""
    lines = []
    
    lines.append(f"\n{'='*60}")
    lines.append(f"MARKETS ({len(markets)} found)")
    lines.append('='*60)
    
    for i, market in enumerate(markets, 1):
        lines.append(f"\n{i}. {market.get('question', market.get('groupItemTitle', 'N/A'))}")
        lines.append(f"   Slug: {market.get('slug', 'N/A')}")
        
        # Outcome prices
        outcome_prices = market.get('outcomePrices', '[]')
        if isinstance(outcome_prices, str):
            try:
                outcome_prices = json.loads(outcome_prices)
            except:
                outcome_prices = []
        
        outcomes = market.get('outcomes', '[]')
        if isinstance(outcomes, str):
            try:
                outcomes = json.loads(outcomes)
            except:
                outcomes = []
        
        if outcome_prices and outcomes:
            prices_str = []
            for outcome, price in zip(outcomes, outcome_prices):
                try:
                    price_pct = float(price) * 100
                    prices_str.append(f"{outcome}: {price_pct:.1f}%")
                except:
                    prices_str.append(f"{outcome}: {price}")
            lines.append(f"   Prices: {' | '.join(prices_str)}")
        
        if market.get('volume'):
            lines.append(f"   Volume: ${float(market.get('volume', 0)):,.2f}")
        
        if market.get('liquidity'):
            lines.append(f"   Liquidity: ${float(market.get('liquidity', 0)):,.2f}")
    
    return '\n'.join(lines)


def format_tags(tags: list) -> str:
    """Format tags list for display."""
    lines = []
    
    lines.append(f"\n{'='*60}")
    lines.append(f"AVAILABLE TAGS ({len(tags)} found)")
    lines.append('='*60)
    
    # Sort by label
    sorted_tags = sorted(tags, key=lambda x: x.get('label', '').lower())
    
    for tag in sorted_tags:
        tag_id = tag.get('id', 'N/A')
        label = tag.get('label', 'N/A')
        slug = tag.get('slug', '')
        lines.append(f"  ID: {tag_id:8} | {label}")
    
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='Polymarket Reader - Fetch and analyze prediction markets',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python polymarket_reader.py --search "bitcoin"
  python polymarket_reader.py --slug "fed-decision-in-october"
  python polymarket_reader.py --tag 100381
  python polymarket_reader.py --list-tags
        """
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '--search', '-s',
        type=str,
        help='Search markets by keyword'
    )
    group.add_argument(
        '--slug',
        type=str,
        help='Fetch event by slug (from Polymarket URL)'
    )
    group.add_argument(
        '--tag', '-t',
        type=int,
        help='Fetch markets by tag ID'
    )
    group.add_argument(
        '--list-tags',
        action='store_true',
        help='List all available tags'
    )
    
    parser.add_argument(
        '--include-closed',
        action='store_true',
        help='Include closed markets (default: only active)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=50,
        help='Max results per page for pagination (default: 50)'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output raw JSON instead of formatted text'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        help='Save output to file'
    )
    
    args = parser.parse_args()
    
    try:
        result = None
        formatted = ""
        
        if args.search:
            result = search_markets(args.search, args.limit, args.include_closed)
            formatted = format_search_results(result)
        
        elif args.slug:
            # Try event first, then market
            try:
                result = fetch_event_by_slug(args.slug)
                formatted = format_event(result)
            except requests.HTTPError as e:
                if e.response.status_code == 404:
                    print("Event not found, trying market...")
                    result = fetch_market_by_slug(args.slug)
                    formatted = format_markets([result])
                else:
                    raise
        
        elif args.tag:
            result = fetch_events_by_tag(args.tag, args.limit, args.include_closed)
            if not result:
                result = fetch_markets_by_tag(args.tag, args.limit, args.include_closed)
                formatted = format_markets(result)
            else:
                # Format events with their markets
                lines = []
                for event in result:
                    lines.append(format_event(event))
                formatted = '\n'.join(lines)
        
        elif args.list_tags:
            result = list_tags()
            formatted = format_tags(result)
        
        # Output
        if args.json:
            output = json.dumps(result, indent=2)
        else:
            output = formatted
        
        print(output)
        
        # Save to file if specified
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            print(f"\nOutput saved to: {args.output}")
    
    except requests.HTTPError as e:
        print(f"HTTP Error: {e}", file=sys.stderr)
        if e.response:
            print(f"Response: {e.response.text}", file=sys.stderr)
        sys.exit(1)
    except requests.RequestException as e:
        print(f"Request Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()


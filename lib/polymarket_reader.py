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
import re
from datetime import datetime


BASE_URL = "https://gamma-api.polymarket.com"


def search_markets(keyword: str, limit: int = 20, include_closed: bool = False) -> dict:
    """
    Search for markets by keyword using multiple API endpoints for comprehensive results.
    
    Args:
        keyword: Search term
        limit: Max events to return
        include_closed: Include closed markets
    
    Returns:
        Dictionary with matching events and tags
    """
    print(f"Searching for: '{keyword}' (limit: {limit})")
    
    all_events = []
    tags = []
    existing_slugs = set()
    keyword_lower = keyword.lower()
    
    # First, get results from public-search (most relevant)
    try:
        response = requests.get(
            f"{BASE_URL}/public-search",
            params={'q': keyword},
            timeout=30
        )
        response.raise_for_status()
        results = response.json()
        for event in results.get('events', []):
            if event.get('slug') not in existing_slugs:
                all_events.append(event)
                existing_slugs.add(event.get('slug'))
        tags = results.get('tags', [])
        print(f"  public-search returned {len(results.get('events', []))} events")
    except Exception as e:
        print(f"  public-search failed: {e}")
    
    # Second, try the events endpoint with title_contains parameter
    if len(all_events) < limit:
        try:
            response = requests.get(
                f"{BASE_URL}/events",
                params={
                    'title_contains': keyword,
                    'limit': min(limit * 5, 200),  # Fetch extra to account for filtering
                    'closed': str(include_closed).lower(),
                    'order': 'volume',
                    'ascending': 'false'
                },
                timeout=30
            )
            response.raise_for_status()
            events_data = response.json()
            added_count = 0
            for event in events_data:
                if event.get('slug') in existing_slugs:
                    continue
                # Double-check that keyword is actually in title (API filter can be loose)
                title = (event.get('title') or '').lower()
                if keyword_lower in title:
                    all_events.append(event)
                    existing_slugs.add(event.get('slug'))
                    added_count += 1
            print(f"  title_contains returned {len(events_data)} events, {added_count} matched keyword")
        except Exception as e:
            print(f"  title_contains search failed: {e}")
    
    # Third, search markets endpoint and get their parent events
    if len(all_events) < limit:
        try:
            response = requests.get(
                f"{BASE_URL}/markets",
                params={
                    'limit': 200,
                    'closed': str(include_closed).lower(),
                    'order': 'volume',
                    'ascending': 'false'
                },
                timeout=30
            )
            response.raise_for_status()
            markets_data = response.json()
            
            # Check if keyword is in market question/title
            for market in markets_data:
                question = (market.get('question') or '').lower()
                group_title = (market.get('groupItemTitle') or '').lower()
                
                if keyword_lower in question or keyword_lower in group_title:
                    # Get the parent event slug
                    event_slug = market.get('eventSlug')
                    if event_slug and event_slug not in existing_slugs:
                        # Fetch the full event
                        try:
                            event_resp = requests.get(f"{BASE_URL}/events/slug/{event_slug}", timeout=10)
                            if event_resp.ok:
                                event = event_resp.json()
                                all_events.append(event)
                                existing_slugs.add(event_slug)
                        except:
                            pass
                        
                        if len(all_events) >= limit:
                            break
            
            print(f"  Markets search added events, total: {len(all_events)}")
        except Exception as e:
            print(f"  markets search failed: {e}")
    
    # Fourth, fetch more events and filter client-side with looser matching
    if len(all_events) < limit:
        try:
            response = requests.get(
                f"{BASE_URL}/events",
                params={
                    'limit': 500,  # Fetch more to find matches
                    'closed': str(include_closed).lower(),
                    'order': 'volume',
                    'ascending': 'false'
                },
                timeout=30
            )
            response.raise_for_status()
            additional_events = response.json()
            
            # Filter events that contain the keyword (case-insensitive substring match)
            for event in additional_events:
                if event.get('slug') in existing_slugs:
                    continue
                    
                title = (event.get('title') or '').lower()
                description = (event.get('description') or '').lower()
                
                # Check if keyword is in title or description (substring match)
                if keyword_lower in title or keyword_lower in description:
                    all_events.append(event)
                    existing_slugs.add(event.get('slug'))
                    
                    if len(all_events) >= limit:
                        break
                        
            print(f"  After client-side filtering: {len(all_events)} events")
        except Exception as e:
            print(f"  events fetch failed: {e}")
    
    # Filter out closed events if requested
    if not include_closed:
        all_events = [e for e in all_events if not e.get('closed', False)]
    
    # Apply limit
    all_events = all_events[:limit]
    
    print(f"  Final: {len(all_events)} events, {len(tags)} tags")
    
    return {'events': all_events, 'tags': tags}


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


# CLOB API for price history
CLOB_API_URL = "https://clob.polymarket.com"


def get_clob_token_ids(event_slug: str, market_index: int = 0) -> tuple:
    """
    Get the CLOB token IDs for a market within an event.
    
    Args:
        event_slug: Event slug from Polymarket URL
        market_index: Index of market within the event (default: 0)
    
    Returns:
        Tuple of (yes_token_id, no_token_id, market_question)
    """
    response = requests.get(f"{BASE_URL}/events/slug/{event_slug}", timeout=30)
    response.raise_for_status()
    event = response.json()
    
    markets = event.get('markets', [])
    if market_index >= len(markets):
        raise ValueError(f"Market index {market_index} out of range. Event has {len(markets)} markets.")
    
    market = markets[market_index]
    token_ids = market.get('clobTokenIds', [])
    
    if isinstance(token_ids, str):
        token_ids = json.loads(token_ids)
    
    yes_token = token_ids[0] if len(token_ids) > 0 else None
    no_token = token_ids[1] if len(token_ids) > 1 else None
    
    return yes_token, no_token, market.get('question')


def fetch_price_history(
    token_id: str,
    interval: str = "max",
    fidelity: int = 1440
) -> list:
    """
    Fetch price history for a market token.
    
    Args:
        token_id: CLOB token ID
        interval: Time interval ('1m', '1h', '6h', '1d', '1w', 'max')
        fidelity: Resolution in minutes (e.g., 60=hourly, 1440=daily)
    
    Returns:
        List of {t: timestamp, p: price} dictionaries
    """
    params = {
        'market': token_id,
        'interval': interval,
        'fidelity': fidelity
    }
    
    response = requests.get(f"{CLOB_API_URL}/prices-history", params=params, timeout=30)
    response.raise_for_status()
    data = response.json()
    
    return data.get('history', [])


def get_market_price_history(event_slug: str, market_index: int = 0, fidelity: int = 1440) -> dict:
    """
    Get full price history for a market.
    
    Args:
        event_slug: Event slug
        market_index: Index of market within event
        fidelity: Resolution in minutes (1440=daily, 60=hourly)
    
    Returns:
        Dictionary with market info and price history
    """
    # Get token IDs
    yes_token, no_token, question = get_clob_token_ids(event_slug, market_index)
    
    if not yes_token:
        return {'error': 'Could not find token ID for this market'}
    
    # Fetch price history
    history = fetch_price_history(yes_token, interval="max", fidelity=fidelity)
    
    return {
        'event_slug': event_slug,
        'question': question,
        'token_id': yes_token,
        'outcome': 'Yes',
        'fidelity_minutes': fidelity,
        'data_points': len(history),
        'history': history
    }


def get_all_markets_price_history(event_slug: str, fidelity: int = 60) -> dict:
    """
    Get price history for ALL markets in an event.
    
    Args:
        event_slug: Event slug
        fidelity: Resolution in minutes (60=hourly, 1440=daily)
    
    Returns:
        Dictionary with event info and price history for all markets
    """
    # Fetch the event first
    response = requests.get(f"{BASE_URL}/events/slug/{event_slug}", timeout=30)
    response.raise_for_status()
    event = response.json()
    
    markets = event.get('markets', [])
    all_histories = []
    
    # Define colors for different outcomes
    colors = [
        '#f97316',  # orange
        '#3b82f6',  # blue
        '#22c55e',  # green
        '#eab308',  # yellow
        '#ec4899',  # pink
        '#8b5cf6',  # purple
        '#06b6d4',  # cyan
        '#ef4444',  # red
        '#84cc16',  # lime
        '#f59e0b',  # amber
    ]
    
    for i, market in enumerate(markets):
        # Skip closed markets
        if market.get('closed'):
            continue
            
        token_ids = market.get('clobTokenIds', [])
        if isinstance(token_ids, str):
            token_ids = json.loads(token_ids)
        
        if not token_ids:
            continue
            
        yes_token = token_ids[0]
        
        # Get outcome name
        name = market.get('groupItemTitle') or market.get('question') or f'Outcome {i+1}'
        
        # Get current probability
        outcome_prices = market.get('outcomePrices', '[]')
        if isinstance(outcome_prices, str):
            try:
                outcome_prices = json.loads(outcome_prices)
            except:
                outcome_prices = []
        current_prob = float(outcome_prices[0]) if outcome_prices else 0
        
        try:
            # Fetch price history
            history = fetch_price_history(yes_token, interval="max", fidelity=fidelity)
            
            if history:
                all_histories.append({
                    'name': name,
                    'token_id': yes_token,
                    'current_probability': current_prob,
                    'color': colors[i % len(colors)],
                    'history': history
                })
        except Exception as e:
            print(f"Error fetching history for {name}: {e}")
            continue
    
    return {
        'event_slug': event_slug,
        'title': event.get('title'),
        'fidelity_minutes': fidelity,
        'markets': all_histories
    }


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


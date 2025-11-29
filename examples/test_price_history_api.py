#!/usr/bin/env python3
"""
Test script for Polymarket Price History API
https://docs.polymarket.com/api-reference/pricing/get-price-history-for-a-traded-token

Endpoint: https://clob.polymarket.com/prices-history

This API provides FULL historical price data back to market creation!
"""

import requests
from datetime import datetime
import json

CLOB_API_URL = "https://clob.polymarket.com"
GAMMA_API_URL = "https://gamma-api.polymarket.com"


def get_clob_token_ids(event_slug: str, market_index: int = 0) -> tuple:
    """
    Get the CLOB token IDs for a market within an event.
    
    Args:
        event_slug: Event slug from Polymarket URL
        market_index: Index of market within the event (default: 0)
    
    Returns:
        Tuple of (yes_token_id, no_token_id, market_question)
    """
    response = requests.get(f"{GAMMA_API_URL}/events/slug/{event_slug}", timeout=30)
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
    fidelity: int = 1440,
    start_ts: int = None,
    end_ts: int = None
) -> list:
    """
    Fetch price history for a market token.
    
    Args:
        token_id: CLOB token ID
        interval: Time interval ('1m', '1h', '6h', '1d', '1w', 'max')
        fidelity: Resolution in minutes (e.g., 60=hourly, 1440=daily)
        start_ts: Start Unix timestamp (optional)
        end_ts: End Unix timestamp (optional)
    
    Returns:
        List of {t: timestamp, p: price} dictionaries
    """
    params = {
        'market': token_id,
        'interval': interval,
        'fidelity': fidelity
    }
    
    if start_ts:
        params['startTs'] = start_ts
    if end_ts:
        params['endTs'] = end_ts
    
    response = requests.get(f"{CLOB_API_URL}/prices-history", params=params, timeout=30)
    response.raise_for_status()
    data = response.json()
    
    return data.get('history', [])


def format_price_history(history: list) -> str:
    """Format price history for display."""
    lines = []
    lines.append(f"{'Date':<20} {'Price':>10}")
    lines.append("-" * 32)
    
    for h in history:
        dt = datetime.fromtimestamp(h['t']).strftime('%Y-%m-%d %H:%M')
        price = h['p']
        lines.append(f"{dt:<20} {price:>10.4f}")
    
    return '\n'.join(lines)


def main():
    # Test with US Recession 2025 market (has long history)
    event_slug = "us-recession-in-2025"
    
    print("="*60)
    print("POLYMARKET PRICE HISTORY API TEST")
    print("="*60)
    print(f"\nEvent: {event_slug}")
    
    # Get CLOB token IDs
    yes_token, no_token, question = get_clob_token_ids(event_slug)
    print(f"Market: {question}")
    print(f"Yes Token ID: {yes_token[:30]}...")
    print(f"No Token ID: {no_token[:30]}...")
    
    # Fetch daily price history for YES token
    print(f"\nFetching daily price history (YES outcome)...")
    history = fetch_price_history(yes_token, interval="max", fidelity=1440)
    
    print(f"Data points: {len(history)}")
    
    if history:
        oldest = min(h['t'] for h in history)
        newest = max(h['t'] for h in history)
        oldest_dt = datetime.fromtimestamp(oldest)
        newest_dt = datetime.fromtimestamp(newest)
        
        print(f"\nDate range:")
        print(f"  Oldest: {oldest_dt}")
        print(f"  Newest: {newest_dt}")
        print(f"  Span: {(newest_dt - oldest_dt).days} days")
        
        # Show sample data
        print(f"\nFirst 5 data points:")
        print(format_price_history(history[:5]))
        
        print(f"\nLast 5 data points:")
        print(format_price_history(history[-5:]))
        
        # Calculate some stats
        prices = [h['p'] for h in history]
        print(f"\nPrice Statistics:")
        print(f"  Min: {min(prices):.4f}")
        print(f"  Max: {max(prices):.4f}")
        print(f"  Current: {prices[-1]:.4f}")
        print(f"  Change: {(prices[-1] - prices[0]):.4f} ({(prices[-1]/prices[0] - 1)*100:+.1f}%)")
    
    # Save to JSON
    output_file = "examples/output/recession_price_history.json"
    output_data = {
        "event_slug": event_slug,
        "question": question,
        "token_id": yes_token,
        "outcome": "Yes",
        "fidelity_minutes": 1440,
        "history": history
    }
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    print(f"\nSaved to: {output_file}")


if __name__ == '__main__':
    main()



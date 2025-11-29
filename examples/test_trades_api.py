#!/usr/bin/env python3
"""
Test script for Polymarket Trades API
https://docs.polymarket.com/api-reference/core/get-trades-for-a-user-or-markets

Endpoint: https://data-api.polymarket.com/trades
"""

import requests
from datetime import datetime
import json

DATA_API_URL = "https://data-api.polymarket.com"
GAMMA_API_URL = "https://gamma-api.polymarket.com"


def get_condition_id(event_slug: str, market_index: int = 0) -> tuple:
    """
    Get the condition ID for a market within an event.
    
    Args:
        event_slug: Event slug from Polymarket URL
        market_index: Index of market within the event (default: 0 = first market)
    
    Returns:
        Tuple of (condition_id, market_question)
    """
    response = requests.get(f"{GAMMA_API_URL}/events/slug/{event_slug}", timeout=30)
    response.raise_for_status()
    event = response.json()
    
    markets = event.get('markets', [])
    if market_index >= len(markets):
        raise ValueError(f"Market index {market_index} out of range. Event has {len(markets)} markets.")
    
    market = markets[market_index]
    return market.get('conditionId'), market.get('question')


def fetch_trades(
    condition_id: str,
    limit: int = 100,
    offset: int = 0,
    side: str = None,
    taker_only: bool = True
) -> list:
    """
    Fetch trade history for a market.
    
    Args:
        condition_id: Market condition ID (0x-prefixed 64-hex string)
        limit: Max trades to return (max 10000)
        offset: Pagination offset
        side: Filter by side ('BUY' or 'SELL')
        taker_only: Only return taker trades (default: True)
    
    Returns:
        List of trade dictionaries
    """
    params = {
        'market': condition_id,
        'limit': limit,
        'offset': offset,
        'takerOnly': str(taker_only).lower()
    }
    
    if side:
        params['side'] = side
    
    response = requests.get(f"{DATA_API_URL}/trades", params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def format_trades(trades: list) -> str:
    """Format trades for display."""
    lines = []
    lines.append(f"{'Time':<20} {'Side':<6} {'Price':>8} {'Size':>12} {'Outcome':<10}")
    lines.append("-" * 60)
    
    for t in trades:
        ts = t.get('timestamp', 0)
        dt = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S') if ts else 'N/A'
        side = t.get('side', 'N/A')
        price = t.get('price', 0)
        size = t.get('size', 0)
        outcome = t.get('outcome', 'N/A')
        
        lines.append(f"{dt:<20} {side:<6} {price:>8.2f} {size:>12.2f} {outcome:<10}")
    
    return '\n'.join(lines)


def main():
    # Test with NVDA market
    event_slug = "what-will-nvda-hit-before-2026"
    
    print("="*60)
    print("POLYMARKET TRADES API TEST")
    print("="*60)
    print(f"\nEvent: {event_slug}")
    
    # Get condition ID for first market
    condition_id, question = get_condition_id(event_slug, market_index=0)
    print(f"Market: {question}")
    print(f"Condition ID: {condition_id}")
    
    # Fetch trades
    print(f"\nFetching trades...")
    trades = fetch_trades(condition_id, limit=20)
    
    print(f"\nTrades found: {len(trades)}")
    print()
    print(format_trades(trades))
    
    # Summary stats
    if trades:
        total_volume = sum(t.get('size', 0) * t.get('price', 0) for t in trades)
        buy_count = sum(1 for t in trades if t.get('side') == 'BUY')
        sell_count = sum(1 for t in trades if t.get('side') == 'SELL')
        
        print(f"\n{'='*60}")
        print("SUMMARY")
        print(f"{'='*60}")
        print(f"Total trades: {len(trades)}")
        print(f"Buy orders: {buy_count}")
        print(f"Sell orders: {sell_count}")
        print(f"Volume (in sample): ${total_volume:,.2f}")
    
    # Save to JSON
    output_file = "examples/output/nvda_trades_sample.json"
    with open(output_file, 'w') as f:
        json.dump(trades, f, indent=2)
    print(f"\nSaved to: {output_file}")


if __name__ == '__main__':
    main()



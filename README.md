# Sourcer

A collection of Python tools for gathering and analyzing financial data from various sources.

## Tools

### 1. Polymarket Reader (`polymarket_reader.py`)

Fetch and analyze prediction markets from Polymarket.

```bash
# Search markets by keyword
python polymarket_reader.py --search "bitcoin"

# Fetch specific event by slug
python polymarket_reader.py --slug "what-will-googl-hit-before-2026"

# Fetch markets by tag ID
python polymarket_reader.py --tag 100381

# List all available tags
python polymarket_reader.py --list-tags

# Output as JSON
python polymarket_reader.py --search "GOOGL" --json

# Save to file
python polymarket_reader.py --search "Fed" --output fed_markets.txt
```

### 2. GOOGL Distribution Analysis (`googl_distribution.py`)

Analyze GOOGL stock price probabilities based on Polymarket prediction market data.

- Converts touch probabilities to terminal distribution using reflection principle
- Fits Gaussian Mixture Model for smooth interpolation
- Calculates P(stock up) and percentiles

```bash
python googl_distribution.py
```

### 3. Twitter Reader (`twitter_reader.py`)

Fetch Twitter/X analysis using FinChat COT API.

```bash
python twitter_reader.py --accounts "@elonmusk,@sama" --topic "AI" --timeframe "7 days" --post_count 20
```

### 4. Twitter Batch Reader (`twitter_reader_batch.py`)

Run Twitter analysis for multiple accounts and consolidate results.

```bash
python twitter_reader_batch.py
```

## Data Sources

- **Polymarket**: Prediction market data via Gamma API (`https://gamma-api.polymarket.com`)
- **FinChat**: COT API for Twitter/X analysis
- **Alpha Vantage**: Stock price data (via MCP)

## Requirements

```bash
pip install requests matplotlib numpy scipy
```

## Output Files

- `googl_distribution.png` - Price probability distribution chart
- `consolidated_report_*.md` - Twitter analysis reports
- `*_markets_data.json` - Raw market data from Polymarket
- `*_markets_summary.md` - Formatted market summaries


# Sourcer

Financial data aggregation tools for Polymarket prediction markets and Twitter/X analysis.

## Project Structure

```
sourcer/
├── app.py                  # FastAPI app (Railway deployment)
├── api/                    # Vercel serverless functions
│   ├── polymarket.py       # /api/polymarket endpoint
│   └── twitter.py          # /api/twitter endpoint
├── lib/                    # Core library code
│   ├── polymarket_reader.py
│   ├── twitter_reader.py
│   └── twitter_reader_batch.py
├── examples/               # Example scripts & outputs
│   ├── googl_distribution.py
│   └── output/
├── docs/                   # Documentation
├── vercel.json             # Vercel config
├── Procfile                # Railway config
└── requirements.txt
```

## Quick Start

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run Locally (FastAPI)

```bash
uvicorn app:app --reload
```

Then visit: http://localhost:8000

### CLI Usage

```bash
# Search Polymarket
python lib/polymarket_reader.py --search "bitcoin"

# Get specific event
python lib/polymarket_reader.py --slug "what-will-googl-hit-before-2026"

# Twitter analysis
python lib/twitter_reader.py --accounts "@elonmusk" --topic "AI" --timeframe "7 days"
```

## API Endpoints

### Polymarket

| Endpoint | Description |
|----------|-------------|
| `GET /polymarket/search?q=keyword` | Search markets by keyword |
| `GET /polymarket/event/{slug}` | Get event details by slug |
| `GET /polymarket/tags` | List all available tags |

### Twitter

| Endpoint | Description |
|----------|-------------|
| `GET /api/twitter?accounts=@handle&topic=AI` | Analyze Twitter accounts |

## Deployment

### Railway

1. Connect your GitHub repo to Railway
2. Railway auto-detects the `Procfile`
3. Deploy!

### Vercel

1. Connect your GitHub repo to Vercel
2. Vercel auto-detects `vercel.json`
3. Deploy!

The `api/` folder becomes serverless endpoints:
- `/api/polymarket`
- `/api/twitter`

## Data Sources

- **Polymarket**: Gamma API (`https://gamma-api.polymarket.com`)
- **Twitter/X**: FinChat COT API
- **Stock Prices**: Alpha Vantage (via MCP)

## Examples

See `examples/` folder for analysis scripts:

- `googl_distribution.py` - GOOGL price probability analysis from Polymarket data

## License

MIT

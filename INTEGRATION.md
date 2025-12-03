# Reddit Reader Integration Guide

This guide shows how to integrate the Reddit Reader into your own Python projects.

## Installation

Copy these files into your project:
- `reddit_client.py` - The main Reddit client
- `config.py` - Configuration settings

Install dependencies:
```bash
pip install requests
```

## Quick Start

```python
from reddit_client import RedditClient

# Initialize client
client = RedditClient()

# Fetch posts from a subreddit
posts = client.get_posts("TheAllinPodcasts", sort="hot", limit=10)

for post in posts:
    print(f"{post['title']} - {post['score']} pts")
```

---

## API Reference

### RedditClient

#### `get_posts(subreddit, sort='hot', limit=25, time_filter='all', after=None)`

Fetch posts from a subreddit.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `subreddit` | str | required | Subreddit name (without r/) |
| `sort` | str | `'hot'` | Sort method: `'hot'`, `'new'`, `'top'`, `'rising'` |
| `limit` | int | `25` | Number of posts (max 100) |
| `time_filter` | str | `'all'` | For `top` sort: `'hour'`, `'day'`, `'week'`, `'month'`, `'year'`, `'all'` |
| `after` | str | `None` | Pagination token for next batch |

**Returns:** List of post dictionaries

**Post Dictionary Fields:**
```python
{
    'post_id': str,        # Reddit's unique ID (e.g., '1mtzt1q')
    'subreddit': str,      # Subreddit name
    'title': str,          # Post title
    'author': str,         # Username
    'created_utc': int,    # Unix timestamp
    'score': int,          # Upvotes - downvotes
    'num_comments': int,   # Comment count
    'url': str,            # Link URL (for link posts)
    'selftext': str,       # Post body (for text posts)
    'permalink': str,      # Reddit permalink (e.g., '/r/sub/comments/...')
    'is_video': bool,      # Video flag
}
```

---

#### `get_comments(subreddit, post_id, limit=500)`

Fetch comments for a specific post.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `subreddit` | str | required | Subreddit name |
| `post_id` | str | required | Post ID from `get_posts()` |
| `limit` | int | `500` | Max comments to fetch |

**Returns:** List of comment dictionaries

**Comment Dictionary Fields:**
```python
{
    'comment_id': str,     # Reddit's unique ID
    'post_id': str,        # Parent post ID
    'parent_id': str,      # Parent comment ID (for replies)
    'author': str,         # Username
    'body': str,           # Comment text
    'created_utc': int,    # Unix timestamp
    'score': int,          # Upvotes - downvotes
    'depth': int,          # Nesting level (0 = top-level)
}
```

---

#### `extract_subreddit_from_url(url)`

Extract subreddit name from a Reddit URL.

```python
client = RedditClient()
subreddit = client.extract_subreddit_from_url("https://www.reddit.com/r/TheAllinPodcasts/")
# Returns: "TheAllinPodcasts"
```

---

## Integration Examples

### Example 1: Fetch Posts and Comments

```python
from reddit_client import RedditClient

client = RedditClient()

# Get top 5 posts from last week
posts = client.get_posts("TheAllinPodcasts", sort="top", limit=5, time_filter="week")

for post in posts:
    print(f"\n📝 {post['title']}")
    print(f"   Score: {post['score']} | Comments: {post['num_comments']}")
    
    # Fetch comments for this post
    comments = client.get_comments("TheAllinPodcasts", post['post_id'])
    
    for comment in comments[:3]:  # First 3 comments
        print(f"   💬 {comment['author']}: {comment['body'][:50]}...")
```

---

### Example 2: Save to JSON

```python
import json
from reddit_client import RedditClient

client = RedditClient()

# Fetch data
posts = client.get_posts("TheAllinPodcasts", limit=25)

data = []
for post in posts:
    comments = client.get_comments("TheAllinPodcasts", post['post_id'])
    data.append({
        'post': post,
        'comments': comments
    })

# Save to JSON
with open('reddit_data.json', 'w') as f:
    json.dump(data, f, indent=2)
```

---

### Example 3: Stream to Database

```python
import sqlite3
from reddit_client import RedditClient

client = RedditClient()

# Setup database
conn = sqlite3.connect('my_reddit.db')
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS posts (
        post_id TEXT PRIMARY KEY,
        title TEXT,
        author TEXT,
        score INTEGER,
        created_utc INTEGER
    )
''')

# Fetch and insert
posts = client.get_posts("TheAllinPodcasts", limit=50)

for post in posts:
    cursor.execute('''
        INSERT OR REPLACE INTO posts (post_id, title, author, score, created_utc)
        VALUES (?, ?, ?, ?, ?)
    ''', (post['post_id'], post['title'], post['author'], post['score'], post['created_utc']))

conn.commit()
conn.close()
```

---

### Example 4: Pagination (Fetch More Than 100 Posts)

```python
from reddit_client import RedditClient

client = RedditClient()

all_posts = []
after = None

# Fetch 300 posts in batches of 100
for _ in range(3):
    posts = client.get_posts("TheAllinPodcasts", sort="new", limit=100, after=after)
    
    if not posts:
        break
    
    all_posts.extend(posts)
    
    # Get pagination token for next batch
    # Note: You need to get 'after' from the API response
    # This requires modifying get_posts() to return it

print(f"Total posts fetched: {len(all_posts)}")
```

---

### Example 5: Filter Posts by Keywords

```python
from reddit_client import RedditClient

client = RedditClient()

posts = client.get_posts("TheAllinPodcasts", sort="new", limit=100)

# Filter for posts mentioning specific keywords
keywords = ['sacks', 'chamath', 'friedberg', 'jason']

filtered = [
    post for post in posts
    if any(kw in post['title'].lower() for kw in keywords)
]

print(f"Found {len(filtered)} posts mentioning the hosts:")
for post in filtered:
    print(f"  - {post['title']}")
```

---

### Example 6: Convert to Pandas DataFrame

```python
import pandas as pd
from reddit_client import RedditClient

client = RedditClient()

posts = client.get_posts("TheAllinPodcasts", limit=50)

# Convert to DataFrame
df = pd.DataFrame(posts)

# Convert timestamp to datetime
df['created_date'] = pd.to_datetime(df['created_utc'], unit='s')

# Analysis
print(df[['title', 'score', 'num_comments', 'created_date']].head(10))
print(f"\nAverage score: {df['score'].mean():.1f}")
print(f"Total comments: {df['num_comments'].sum()}")
```

---

## Rate Limiting

The client automatically rate-limits requests (2 seconds between requests). This is configured in `config.py`:

```python
# config.py
REQUEST_DELAY_SECONDS = 2  # Adjust if needed
```

⚠️ **Warning:** Don't set this too low or Reddit may block your requests.

---

## Error Handling

```python
from reddit_client import RedditClient

client = RedditClient()

posts = client.get_posts("NonExistentSubreddit123456", limit=10)

if not posts:
    print("No posts found - subreddit may not exist or be private")
else:
    print(f"Found {len(posts)} posts")
```

---

## Configuration

Edit `config.py` to customize:

```python
# User-Agent (required by Reddit)
USER_AGENT = "MyApp/1.0 (by u/your_username)"

# Rate limiting
REQUEST_DELAY_SECONDS = 2

# Defaults
DEFAULT_POST_LIMIT = 25
MAX_POST_LIMIT = 100

# Reddit base URL
REDDIT_BASE_URL = "https://www.reddit.com"
```


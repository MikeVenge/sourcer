# Bucketeer API Examples

This document provides examples of how to interact with the Bucketeer API, which automatically classifies content into buckets using vector embeddings.

## Authentication

All API requests require authentication using an API key in the Authorization header:

```bash
Authorization: Bearer bcktr-wxFrNg7Co6MbtvQdtpk39lK0TPALbW5T
```

Set your API key as an environment variable:
```bash
export API_KEY="bcktr-wxFrNg7Co6MbtvQdtpk39lK0TPALbW5T"
```

## Base URL

use this URL as the base URL:  https://bucketeer.adgo-infra.com/

## Endpoints

### 1. List Buckets

Retrieve all available buckets for content classification.

**Endpoint:** `GET /api/v1/buckets/`

**Example:**
```python
import httpx

headers = {"Authorization": f"Bearer {API_KEY}"}
response = httpx.get("http://localhost:8000/api/v1/buckets/", headers=headers)
buckets = response.json()["results"]
```

**Response:**
```json
{
  "results": [
    {
      "id": "bucket-uuid",
      "name": "Technology",
      "criteria": "Articles about technology, crypto, and digital innovation"
    }
  ]
}
```

### 2. Create Content (Auto-Classification)

Create content and let the system automatically classify it into the most appropriate bucket using vector embeddings.

**Endpoint:** `POST /api/v1/content/`

**Request Body:**
```json
{
  "content": "Your text content here"
}
```

**Example:**
```python
import httpx

headers = {"Authorization": f"Bearer {API_KEY}"}
text = "Bitcoin extended a tentative rebound on Wednesday..."

response = httpx.post(
    "http://localhost:8000/api/v1/content/",
    json={"content": text},
    headers=headers,
)
```

**Response:**
```json
{
  "id": "content-uuid",
  "content": "Bitcoin extended a tentative rebound...",
  "buckets": ["bucket-uuid"]
}
```

### 3. Create Content (Manual Bucket Assignment)

Create content and explicitly assign it to a specific bucket.

**Endpoint:** `POST /api/v1/content/`

**Request Body:**
```json
{
  "content": "Your text content here",
  "bucket": "bucket-uuid"
}
```

**Example:**
```python
import httpx

headers = {"Authorization": f"Bearer {API_KEY}"}
text = "The U.S. holiday shopping season kicked off..."
bucket_id = "your-bucket-uuid"

response = httpx.post(
    "http://localhost:8000/api/v1/content/",
    json={"content": text, "bucket": bucket_id},
    headers=headers,
)
```

**Response:**
```json
{
  "id": "content-uuid",
  "content": "The U.S. holiday shopping season...",
  "buckets": ["bucket-uuid"]
}
```

### 4. List Content

Retrieve all content items.

**Endpoint:** `GET /api/v1/content/`

**Example:**
```python
import httpx

headers = {"Authorization": f"Bearer {API_KEY}"}
response = httpx.get("http://localhost:8000/api/v1/content/", headers=headers)
content_list = response.json()["results"]
```

## How It Works

### Automatic Classification

When you create content without specifying a bucket:

1. The system generates a vector embedding for your content
2. It compares this embedding against existing bucket criteria
3. The content is automatically assigned to the best-matching bucket
4. If no suitable bucket is found, the content is created without bucket assignment

### Manual Classification

When you specify a bucket ID in your request:

1. The content is directly assigned to the specified bucket
2. No automatic classification occurs
3. Useful when you know exactly which bucket the content belongs to

## Complete Example

See `example.py` for a complete working example:

```python
import httpx
import os

API_KEY = os.environ.get("API_KEY")
headers = {"Authorization": f"Bearer {API_KEY}"}

# Get all available buckets
response = httpx.get("http://localhost:8000/api/v1/buckets/", headers=headers)
buckets = response.json()["results"]

# Create content with auto-classification
response = httpx.post(
    "http://localhost:8000/api/v1/content/",
    json={"content": "Your article text here"},
    headers=headers,
)

# Create content with specific bucket
response = httpx.post(
    "http://localhost:8000/api/v1/content/",
    json={"content": "Your article text here", "bucket": buckets[0]["id"]},
    headers=headers,
)
```

## Response Status Codes

- `200 OK` - Successful GET request
- `201 Created` - Successful POST request (content created)
- `400 Bad Request` - Invalid request data
- `401 Unauthorized` - Missing or invalid API key
- `404 Not Found` - Resource not found

## Notes

- All endpoints require authentication via API key
- Content classification uses vector embeddings for intelligent categorization
- Buckets can be retrieved to understand available categories
- Content can belong to multiple buckets (many-to-many relationship)
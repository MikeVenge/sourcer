# How to Use the FinChat COT API

A comprehensive guide to integrating FinChat's Chain of Thought (COT) API into your applications.

---

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Authentication](#authentication)
- [API v1: Standard COT Execution](#api-v1-standard-cot-execution)
- [API v2: Pre-configured COT Sessions](#api-v2-pre-configured-cot-sessions)
- [Python Implementation](#python-implementation)
- [Error Handling](#error-handling)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

---

## Overview

FinChat provides two API versions for executing Chain of Thought (COT) prompts:

| Feature | API v1 | API v2 |
|---------|--------|--------|
| **Use Case** | Custom COT execution | Pre-configured COT sessions |
| **Session Creation** | You create sessions | Uses existing sessions |
| **COT Selection** | You specify COT slug | COT pre-configured in session |
| **Parameters** | Flexible parameters | Session-specific parameters |
| **Polling** | Poll chats by session | Poll session results |
| **Complexity** | More flexible, more code | Simpler, less code |

---

## Prerequisites

### Required
- **Base URL**: `https://finchat-api.adgo.dev`
- **Python 3.7+** (or any HTTP client)
- **requests** library: `pip install requests`
- **polling2** library (optional): `pip install polling2`

### Optional
- **API Token**: Bearer token for authenticated requests (not always required)

---

## Authentication

### With Authentication
```python
headers = {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer YOUR_API_TOKEN'
}
```

### Without Authentication
```python
headers = {
    'Content-Type': 'application/json'
}
```

Most COT endpoints work without authentication, but may have rate limits.

---

## API v1: Standard COT Execution

Use v1 when you need **full control** over COT selection and parameters.

### Step 1: Create a Session

**Request:**
```http
POST https://finchat-api.adgo.dev/api/v1/sessions/
Content-Type: application/json

{
  "client_id": "your-client-identifier",
  "data_source": "alpha_vantage"
}
```

**Response:**
```json
{
  "id": "67891234abcdef...",
  "client_id": "your-client-identifier",
  "data_source": "alpha_vantage",
  "created_on": "2025-11-24T10:00:00Z"
}
```

### Step 2: Run a COT Prompt

**Request:**
```http
POST https://finchat-api.adgo.dev/api/v1/chats/
Content-Type: application/json

{
  "session": "67891234abcdef...",
  "message": "cot ai-detector-v2 $text:Your text here $purpose:AI detection"
}
```

**Message Format:**
```
cot {cot_slug} $param1:value1 $param2:value2 $param3:value3
```

**Response:**
```json
{
  "id": "chat_id_12345",
  "session": "67891234abcdef...",
  "role": "user",
  "message": "cot ai-detector-v2 $text:...",
  "created_on": "2025-11-24T10:00:01Z"
}
```

### Step 3: Poll for Completion

**Request:**
```http
GET https://finchat-api.adgo.dev/api/v1/chats/?session_id=67891234abcdef...&page_size=500
```

**Look for Response Chat:**
```json
{
  "results": [
    {
      "id": "response_chat_id",
      "respond_to": "chat_id_12345",
      "result_id": "result_67890",
      "metadata": {
        "current_progress": 50,
        "total_progress": 100,
        "current_step": "Step 3/6: Processing..."
      }
    }
  ]
}
```

**Check:**
- Find chat where `respond_to` matches your COT chat ID
- Look for `result_id` (means completed)
- Check `metadata` for progress updates

### Step 4: Get Results

**Request:**
```http
GET https://finchat-api.adgo.dev/api/v1/results/{result_id}/
```

**Response:**
```json
{
  "id": "result_67890",
  "content": "The analysis results...",
  "content_translated": "Translated content if applicable",
  "created_on": "2025-11-24T10:05:00Z"
}
```

---

## API v2: Pre-configured COT Sessions

Use v2 when you have a **pre-configured COT session** and want simpler integration.

### Step 1: Execute COT with Session ID

**Request:**
```http
POST https://finchat-api.adgo.dev/api/v2/sessions/run-cot/{SESSION_ID}/
Content-Type: application/json

{
  "paragraph": "Your text to process"
}
```

**Example:**
```http
POST https://finchat-api.adgo.dev/api/v2/sessions/run-cot/6923bb68658abf729a7b8994/
Content-Type: application/json

{
  "paragraph": "Text to humanize..."
}
```

**Response:**
```json
{
  "id": "new_session_id_98765",
  "client_id": "auto_generated_client",
  "status": "loading",
  "metadata": {},
  "created_on": "2025-11-24T10:00:00Z"
}
```

**Important:** The `id` in the response is a **new session ID** (not a chat ID).

### Step 2: Poll for Results

**Request:**
```http
GET https://finchat-api.adgo.dev/api/v2/sessions/{new_session_id}/results/
```

**Response (Processing):**
```json
{
  "status": "loading",
  "results": []
}
```

**Response (Completed):**
```json
{
  "status": "idle",
  "results": [
    {
      "content": "The processed result...",
      "type": "text"
    }
  ]
}
```

**Check:**
- `status == "idle"` AND `len(results) > 0` means completed
- Extract content from `results[0]["content"]`

---

## Python Implementation

### API v1 Implementation

```python
import requests
import time

class FinChatCOTClient:
    def __init__(self, base_url='https://finchat-api.adgo.dev', api_token=None):
        self.base_url = base_url.rstrip('/')
        self.headers = {'Content-Type': 'application/json'}
        if api_token:
            self.headers['Authorization'] = f'Bearer {api_token}'
    
    def run_cot_v1(self, cot_slug, parameters, timeout=600):
        """Execute COT using v1 API."""
        
        # Step 1: Create session
        session_response = requests.post(
            f"{self.base_url}/api/v1/sessions/",
            json={'client_id': f'client-{int(time.time())}'},
            headers=self.headers
        )
        session_response.raise_for_status()
        session_id = session_response.json()['id']
        
        # Step 2: Build COT message
        param_string = ' '.join([f"${k}:{v}" for k, v in parameters.items()])
        cot_message = f"cot {cot_slug} {param_string}"
        
        # Step 3: Run COT
        chat_response = requests.post(
            f"{self.base_url}/api/v1/chats/",
            json={'session': session_id, 'message': cot_message},
            headers=self.headers
        )
        chat_response.raise_for_status()
        cot_chat_id = chat_response.json()['id']
        
        # Step 4: Poll for completion
        start_time = time.time()
        while time.time() - start_time < timeout:
            chats_response = requests.get(
                f"{self.base_url}/api/v1/chats/",
                params={'session_id': session_id, 'page_size': 500},
                headers=self.headers
            )
            chats_response.raise_for_status()
            chats = chats_response.json()['results']
            
            # Find response chat
            for chat in chats:
                if chat.get('respond_to') == cot_chat_id:
                    # Check for error
                    if chat.get('intent') == 'error':
                        raise RuntimeError(f"COT failed: {chat.get('message')}")
                    
                    # Check for completion
                    result_id = chat.get('result_id')
                    if result_id:
                        # Get result
                        result_response = requests.get(
                            f"{self.base_url}/api/v1/results/{result_id}/",
                            headers=self.headers
                        )
                        result_response.raise_for_status()
                        return result_response.json()['content']
            
            time.sleep(5)  # Wait 5 seconds before next poll
        
        raise TimeoutError("COT execution timed out")

# Usage Example
client = FinChatCOTClient()
result = client.run_cot_v1(
    cot_slug='ai-detector-v2',
    parameters={
        'text': 'Text to analyze...',
        'purpose': 'AI detection'
    },
    timeout=600
)
print(result)
```

### API v2 Implementation

```python
import requests
import time

class FinChatCOTClientV2:
    def __init__(self, base_url='https://finchat-api.adgo.dev', api_token=None):
        self.base_url = base_url.rstrip('/')
        self.headers = {'Content-Type': 'application/json'}
        if api_token:
            self.headers['Authorization'] = f'Bearer {api_token}'
    
    def run_cot_v2(self, session_id, paragraph, timeout=600):
        """Execute COT using v2 API with pre-configured session."""
        
        # Step 1: Execute COT
        response = requests.post(
            f"{self.base_url}/api/v2/sessions/run-cot/{session_id}/",
            json={'paragraph': paragraph},
            headers=self.headers
        )
        response.raise_for_status()
        new_session_id = response.json()['id']
        
        # Step 2: Poll for results
        start_time = time.time()
        results_url = f"{self.base_url}/api/v2/sessions/{new_session_id}/results/"
        
        while time.time() - start_time < timeout:
            response = requests.get(results_url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            
            # Check if completed
            if data['status'] == 'idle' and len(data.get('results', [])) > 0:
                return data['results'][0]['content']
            
            time.sleep(10)  # Wait 10 seconds before next poll
        
        raise TimeoutError("COT execution timed out")

# Usage Example
client = FinChatCOTClientV2()
result = client.run_cot_v2(
    session_id='6923bb68658abf729a7b8994',  # Pre-configured COT session
    paragraph='Text to process...',
    timeout=600
)
print(result)
```

### Using polling2 Library (Recommended)

```python
import requests
import polling2

def run_cot_v2_with_polling2(session_id, paragraph):
    """Cleaner implementation using polling2."""
    
    base_url = 'https://finchat-api.adgo.dev'
    headers = {'Content-Type': 'application/json'}
    
    # Step 1: Execute COT
    response = requests.post(
        f"{base_url}/api/v2/sessions/run-cot/{session_id}/",
        json={'paragraph': paragraph},
        headers=headers
    )
    response.raise_for_status()
    new_session_id = response.json()['id']
    
    # Step 2: Poll with polling2
    def fetch_results():
        response = requests.get(
            f"{base_url}/api/v2/sessions/{new_session_id}/results/",
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    
    def check_success(res):
        return res["status"] == "idle" and len(res.get("results", [])) > 0
    
    data = polling2.poll(
        target=fetch_results,
        check_success=check_success,
        step=10,  # 10 seconds between polls
        timeout=600,  # 10 minutes total
    )
    
    return data["results"][0]["content"]

# Usage
result = run_cot_v2_with_polling2(
    session_id='6923bb68658abf729a7b8994',
    paragraph='Your text here...'
)
print(result)
```

---

## Complete Example: Flask Backend Integration

```python
from flask import Flask, request, jsonify
from flask_cors import CORS
import threading
import uuid
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Job storage
jobs = {}

def process_cot_v2(job_id, session_id, text):
    """Background processing for COT v2."""
    import requests
    import polling2
    
    try:
        jobs[job_id]['status'] = 'processing'
        
        base_url = 'https://finchat-api.adgo.dev'
        headers = {'Content-Type': 'application/json'}
        
        # Execute COT
        response = requests.post(
            f"{base_url}/api/v2/sessions/run-cot/{session_id}/",
            json={'paragraph': text},
            headers=headers
        )
        response.raise_for_status()
        new_session_id = response.json()['id']
        
        # Poll for results
        def fetch_results():
            res = requests.get(
                f"{base_url}/api/v2/sessions/{new_session_id}/results/",
                headers=headers
            )
            res.raise_for_status()
            return res.json()
        
        def check_success(res):
            return res["status"] == "idle" and len(res.get("results", [])) > 0
        
        data = polling2.poll(
            target=fetch_results,
            check_success=check_success,
            step=10,
            timeout=600,
        )
        
        # Success
        jobs[job_id]['status'] = 'completed'
        jobs[job_id]['result'] = data["results"][0]["content"]
        jobs[job_id]['completed_at'] = datetime.utcnow().isoformat()
        
    except Exception as e:
        jobs[job_id]['status'] = 'failed'
        jobs[job_id]['error'] = str(e)

@app.route('/api/analyze', methods=['POST'])
def analyze():
    """Start COT analysis."""
    data = request.get_json()
    text = data.get('text', '')
    
    if not text:
        return jsonify({'error': 'No text provided'}), 400
    
    # Create job
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        'status': 'pending',
        'created_at': datetime.utcnow().isoformat()
    }
    
    # Start background processing
    session_id = '6923bb68658abf729a7b8994'  # Your COT session
    thread = threading.Thread(
        target=process_cot_v2,
        args=(job_id, session_id, text),
        daemon=True
    )
    thread.start()
    
    return jsonify({'job_id': job_id, 'status': 'pending'}), 202

@app.route('/api/status/<job_id>', methods=['GET'])
def status(job_id):
    """Get job status."""
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    job = jobs[job_id]
    response = {
        'job_id': job_id,
        'status': job['status']
    }
    
    if job['status'] == 'completed':
        response['result'] = job['result']
    elif job['status'] == 'failed':
        response['error'] = job.get('error', 'Unknown error')
    
    return jsonify(response)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
```

---

## COT Parameters by Type

### AI Detection COT (`ai-detector-v2`)
```python
parameters = {
    'text': 'Text to analyze for AI content...',
    'purpose': 'AI detection for content analysis'
}
```

### Humanize Text COT
```python
# For v2 API sessions
payload = {
    'paragraph': 'Text to humanize...'
}
```

### Company Analysis COT
```python
parameters = {
    'company_1': 'AAPL',
    'company_2': 'MSFT'
}
```

---

## Error Handling

### Common Errors

**404 Not Found:**
```python
# Wrong endpoint or session doesn't exist
try:
    response = requests.post(url, json=data)
    response.raise_for_status()
except requests.HTTPError as e:
    if e.response.status_code == 404:
        print("Session or endpoint not found")
```

**Error Intent in Chat:**
```python
# Check for error intent in response
if chat.get('intent') == 'error':
    error_msg = chat.get('message', 'COT execution failed')
    raise RuntimeError(f"COT error: {error_msg}")
```

**Timeout:**
```python
try:
    result = run_cot_v2(session_id, text, timeout=600)
except TimeoutError:
    print("COT execution took longer than 10 minutes")
```

---

## Best Practices

### 1. Set Appropriate Timeouts
```python
# COT processing can take 5-15 minutes
timeout = 600  # 10 minutes minimum
interval = 10  # Poll every 10 seconds (not too frequent)
```

### 2. Handle Progress Updates
```python
def progress_callback(progress, status):
    """Show progress to users."""
    if status == 'loading':
        print(f"Processing... (this may take several minutes)")
    else:
        print(f"[{progress}%] {status}")
```

### 3. Use Exponential Backoff for Errors
```python
import time

def poll_with_backoff(url, headers, max_retries=5):
    """Poll with exponential backoff on errors."""
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                raise
```

### 4. Store Session IDs for Reuse
```python
# v1 sessions can be reused
session_id = create_session()
# Store in database or cache
# Reuse for multiple COT calls
```

### 5. Implement Graceful Degradation
```python
try:
    result = client.run_cot_v2(session_id, text)
except Exception as e:
    # Log error
    logger.error(f"COT failed: {e}")
    # Return graceful error to user
    return "Analysis temporarily unavailable. Please try again later."
```

---

## Comparison: v1 vs v2

### When to Use v1
- ✅ Need to choose different COT prompts dynamically
- ✅ Want control over session management
- ✅ Need to pass custom parameters to COT
- ✅ Building a general-purpose COT platform

### When to Use v2
- ✅ Have a pre-configured COT session
- ✅ Want simpler implementation
- ✅ Don't need to switch between different COTs
- ✅ Building a specific feature (like text humanization)

---

## Troubleshooting

### Issue: Chat Never Appears in Session
**Problem:** Polling returns 0 chats
**Solution:** 
- v1: Make sure you're polling with the correct `session_id`
- v2: Poll the NEW session ID returned in the response, not the original

### Issue: Timeout Before Completion
**Problem:** COT takes longer than expected
**Solution:**
- Increase timeout to at least 600 seconds (10 minutes)
- Reduce polling interval to 10 seconds (not 5)
- Check metadata.current_progress for actual progress

### Issue: Empty Results
**Problem:** `results` array is empty even when status is "idle"
**Solution:**
- Wait longer - status may change before results populate
- Check for error chats in the session
- Verify the COT session ID is correct

### Issue: 404 on Results Endpoint
**Problem:** `/api/v2/sessions/{id}/results/` returns 404
**Solution:**
- You're using the wrong session ID
- Use the NEW session ID from the run-cot response
- The original session ID won't work for results

---

## Testing Your Integration

### Quick Test Script

```python
#!/usr/bin/env python3
import requests

API_BASE_URL = "https://finchat-api.adgo.dev"
COT_ID = "6923bb68658abf729a7b8994"

# Test text
test_text = "This is a test paragraph with sufficient words to test the API."

print("Testing FinChat COT API...")

# Step 1: Execute
print("1. Executing COT...")
response = requests.post(
    f"{API_BASE_URL}/api/v2/sessions/run-cot/{COT_ID}/",
    json={'paragraph': test_text}
)
print(f"   Status: {response.status_code}")

if response.status_code in [200, 201]:
    session_id = response.json()['id']
    print(f"   Session ID: {session_id}")
    
    # Step 2: Poll
    print("2. Polling for results...")
    import time
    for i in range(60):  # Try for 10 minutes
        response = requests.get(
            f"{API_BASE_URL}/api/v2/sessions/{session_id}/results/"
        )
        data = response.json()
        
        if data['status'] == 'idle' and len(data.get('results', [])) > 0:
            print(f"   ✓ Completed after {i*10} seconds")
            print(f"\nResult:\n{data['results'][0]['content']}")
            break
        
        print(f"   [{i*10}s] Status: {data['status']}")
        time.sleep(10)
else:
    print(f"   ✗ Failed: {response.text}")
```

---

## Additional Resources

### API Endpoints Summary

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/sessions/` | POST | Create new session |
| `/api/v1/chats/` | POST | Run COT prompt |
| `/api/v1/chats/?session_id=X` | GET | Get session chats |
| `/api/v1/results/{id}/` | GET | Get result content |
| `/api/v2/sessions/run-cot/{id}/` | POST | Execute pre-configured COT |
| `/api/v2/sessions/{id}/results/` | GET | Get session results |

### Recommended Libraries

```bash
pip install requests>=2.31.0
pip install polling2>=0.5.0  # For cleaner polling
pip install flask>=2.3.0     # For backend APIs
pip install flask-cors>=4.0.0  # For CORS support
```

### Example COT Sessions

- **AI Detection**: Create your own with v1 API
- **Text Humanization**: `6923bb68658abf729a7b8994` (v2)
- **Custom COTs**: Contact FinChat for pre-configured sessions

---

## Support

For questions or issues:
1. Check this guide's troubleshooting section
2. Review your API responses for error messages
3. Verify your session IDs and COT configurations
4. Test with the provided example scripts

---

**Last Updated:** November 24, 2025  
**API Version:** v1 and v2  
**Base URL:** https://finchat-api.adgo.dev


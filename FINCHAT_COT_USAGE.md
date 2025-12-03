# Finchat CoT (Chain of Thought) Usage Guide

This guide explains how to use finchat to call a CoT (Chain of Thought) prompt and retrieve results.

## Table of Contents
1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Understanding CoT Prompts](#understanding-cot-prompts)
4. [Methods to Call CoT](#methods-to-call-cot)
5. [API Examples](#api-examples)
6. [Using l2m2 to Call Models](#using-l2m2-to-call-models)
7. [Response Handling](#response-handling)

## Overview

A CoT (Chain of Thought) prompt in finchat is a multi-step workflow that executes a series of prompts sequentially. Each step can:
- Fetch data from various sources
- Perform analysis using LLM models
- Use web search for real-time information
- Generate sub-steps dynamically (Live CoT)

CoT prompts are useful for complex tasks that require multiple steps of reasoning, data fetching, and analysis.

## Prerequisites

1. **Access to finchat instance** with authentication
2. **API authentication token** (JWT token)
3. **l2m2 API endpoint** configured (if using l2m2 for model calls)
4. **Python environment** with required packages:
   ```bash
   pip install requests retrying
   ```

## Understanding CoT Prompts

### CoT Structure

A CoT prompt consists of:
- **Slug**: Unique identifier (e.g., `financial-analysis`)
- **Title**: Display name
- **Type**: Either `internal` (runs finchat commands) or `external` (uses Mercury CoT)
- **Parameters**: Variables that can be passed to the CoT (e.g., `$company_name`, `$quarter`)
- **Prompts**: Ordered list of steps to execute
- **Documents**: Optional documents attached to the CoT
- **System Prompt**: Optional custom system prompt

### Parameter Format

Parameters in CoT prompts use the format: `$parameter_name`

Example:
```
Get financial data for $company_name for $quarter
```

Parameters are passed when calling the CoT.

## Methods to Call CoT

There are two primary ways to call a CoT in finchat:

### Method 1: Via Chat Message (Recommended for Interactive Use)

Call a CoT by sending a chat message with the format:
```
/cot <cot_slug> $param1=value1 $param2=value2
```

Example:
```
/cot financial-analysis $company_name=Tesla $quarter=2024Q3
```

### Method 2: Via REST API (Recommended for Programmatic Access)

Use the finchat REST API to:
1. Create a session
2. Create a chat message with CoT command
3. Poll for results

## API Examples

### Example 1: Basic CoT Call via API

```python
import requests
import time

# Configuration
FINCHAT_BASE_URL = "https://your-finchat-instance.com"
API_TOKEN = "your_jwt_token_here"
COT_SLUG = "financial-analysis"  # Replace with your CoT slug

# Headers
headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

# Step 1: Create or get a session
session_response = requests.post(
    f"{FINCHAT_BASE_URL}/api/v1/session/",
    headers=headers,
    json={}
)
session_data = session_response.json()
session_uid = session_data["uid"]

# Step 2: Create a chat message with CoT command
cot_message = f"/cot {COT_SLUG} $company_name=Tesla $quarter=2024Q3"

chat_response = requests.post(
    f"{FINCHAT_BASE_URL}/api/v1/chat/",
    headers=headers,
    json={
        "session": session_uid,
        "message": cot_message,
        "analysis_model": "gemini-2.5-flash",  # Optional: specify model
        "use_web_search": True  # Optional: enable web search
    }
)
chat_data = chat_response.json()
chat_uid = chat_data["uid"]

# Step 3: Poll for the result
# The CoT execution happens asynchronously, so we need to poll for completion
max_attempts = 60  # Wait up to 5 minutes (60 * 5 seconds)
attempt = 0

while attempt < max_attempts:
    time.sleep(5)  # Wait 5 seconds between checks
    
    # Get the chat with its children (responses)
    chat_details = requests.get(
        f"{FINCHAT_BASE_URL}/api/v1/chat/{chat_uid}/",
        headers=headers
    ).json()
    
    # Check if we have a response chat
    children = chat_details.get("children", [])
    if children:
        result_chat = children[-1]  # Get the latest response
        if result_chat.get("intent") != "loading":
            print("CoT execution completed!")
            print(f"Result: {result_chat['message']}")
            print(f"Metadata: {result_chat.get('metadata', {})}")
            break
    
    attempt += 1
    print(f"Waiting for CoT results... ({attempt}/{max_attempts})")
else:
    print("Timeout waiting for CoT results")
```

### Example 2: Using l2m2 for Model Calls

If you want to use l2m2 to call LLM models directly (bypassing the finchat CoT system), you can use this approach:

**Note:** l2m2 v4 API uses OpenAI-compatible format with Bearer token authentication.

```python
import requests
import os

# Configuration - l2m2 v4 API (OpenAI-compatible)
L2M2_API_URL = os.getenv('L2M2_API_URL', 'https://l2m2.adgo-infra.com/api/v4')
L2M2_API_KEY = os.getenv('L2M2_API_KEY', 'l2m2-uyGbDWdn6TGCXvAISfkfHdGd6Z7UsmoCtLD4y1ARRRU')
L2M2_COMPLETIONS_ENDPOINT = f"{L2M2_API_URL}/chat/completions"

def call_l2m2_with_cot_prompt(prompt: str, model: str = "gemini-2.5-flash"):
    """
    Call l2m2 directly with a CoT-style prompt.
    
    Args:
        prompt: The prompt text
        model: Model to use (e.g., "gemini-2.5-flash", "gpt-4o")
    
    Returns:
        The completion text
    """
    # OpenAI-compatible format
    data = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.1,
    }
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {L2M2_API_KEY}'
    }
    
    response = requests.post(
        L2M2_COMPLETIONS_ENDPOINT,
        headers=headers,
        json=data,
        timeout=90
    )
    
    response.raise_for_status()
    result = response.json()
    
    if result.get("error"):
        raise ValueError(f"l2m2 error: {result['error']}")
    
    # OpenAI format: choices[0].message.content
    if "choices" in result and len(result["choices"]) > 0:
        return result["choices"][0]["message"]["content"]
    else:
        raise ValueError("No completion in response")

# Example usage
prompt = """Research the company Tesla and determine their Q3 2024 revenue.
Then analyze their revenue growth compared to Q2 2024."""

result = call_l2m2_with_cot_prompt(prompt, model="gemini-2.5-flash")
print(result)
```

#### Alternative: Using OpenAI SDK

You can also use the official OpenAI Python SDK with l2m2:

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://l2m2.adgo-infra.com/api/v4",
    api_key="l2m2-uyGbDWdn6TGCXvAISfkfHdGd6Z7UsmoCtLD4y1ARRRU"
)

response = client.chat.completions.create(
    model="gemini-2.5-flash",
    messages=[{"role": "user", "content": "Your prompt here"}],
    temperature=0.2,
)

print(response.choices[0].message.content)
```

### Example 3: Multi-Step CoT with Manual Step Execution

```python
from openai import OpenAI

# Initialize client
client = OpenAI(
    base_url="https://l2m2.adgo-infra.com/api/v4",
    api_key="l2m2-uyGbDWdn6TGCXvAISfkfHdGd6Z7UsmoCtLD4y1ARRRU"
)

def execute_cot_steps(steps: list, model: str = "gemini-2.5-flash"):
    """
    Execute a series of CoT steps sequentially.
    
    Args:
        steps: List of step prompts
        model: Model to use
    
    Returns:
        List of step results
    """
    results = []
    context = ""  # Accumulate context from previous steps
    
    for i, step_prompt in enumerate(steps):
        print(f"Executing step {i+1}/{len(steps)}: {step_prompt[:50]}...")
        
        # Include context from previous steps
        full_prompt = f"{context}\n\n{step_prompt}" if context else step_prompt
        
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": full_prompt}],
            temperature=0.2,
        )
        
        result = response.choices[0].message.content
        results.append({
            "step": i + 1,
            "prompt": step_prompt,
            "result": result
        })
        
        # Add result to context for next step
        context += f"\n\nStep {i+1} result: {result}"
    
    return results

# Example: Multi-step financial analysis
steps = [
    "Get Tesla's revenue for Q3 2024",
    "Get Tesla's revenue for Q2 2024",
    "Calculate the percentage growth between Q2 and Q3 2024",
    "Analyze the factors contributing to this growth"
]

results = execute_cot_steps(steps)
for r in results:
    print(f"\nStep {r['step']}:")
    print(f"Result: {r['result']}")
```

## Using l2m2 to Call Models

The finchat codebase uses l2m2 as a unified interface for calling LLM models. l2m2 v4 provides an **OpenAI-compatible API**.

### l2m2 v4 Configuration

```python
# Base URL and API Key
L2M2_BASE_URL = "https://l2m2.adgo-infra.com/api/v4"
L2M2_API_KEY = "l2m2-uyGbDWdn6TGCXvAISfkfHdGd6Z7UsmoCtLD4y1ARRRU"

# Endpoints (OpenAI-compatible)
# Chat completions: POST /chat/completions
# Responses (structured output): POST /responses
```

### Available Models via l2m2

From the finchat codebase, these models are available:
- `gpt-4o`
- `gemini-2.0-flash`
- `gemini-2.5-pro`
- `gemini-2.5-flash`
- `gpt-4.1`
- `grok-3-latest`
- `grok-4-latest`

### l2m2 v4 Request Format (OpenAI-compatible)

```python
# Headers
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer l2m2-uyGbDWdn6TGCXvAISfkfHdGd6Z7UsmoCtLD4y1ARRRU"
}

# Request body (OpenAI chat completions format)
{
    "model": "gemini-2.5-flash",
    "messages": [
        {
            "role": "user",
            "content": "Your prompt here"
        }
    ],
    "temperature": 0.1
}
```

### Response Format (OpenAI-compatible)

```python
{
    "id": "chatcmpl-xxx",
    "object": "chat.completion",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "The model's response text"
            },
            "finish_reason": "stop"
        }
    ],
    "usage": {
        "prompt_tokens": 100,
        "completion_tokens": 50,
        "total_tokens": 150
    }
}
```

### Structured Output with Pydantic

l2m2 v4 supports structured output using the `responses` endpoint:

```python
from openai import OpenAI
from pydantic import BaseModel

class FinancialData(BaseModel):
    company: str
    revenue: float
    quarter: str

client = OpenAI(
    base_url="https://l2m2.adgo-infra.com/api/v4",
    api_key="l2m2-uyGbDWdn6TGCXvAISfkfHdGd6Z7UsmoCtLD4y1ARRRU"
)

response = client.responses.parse(
    model="gemini-2.5-flash",
    input="Tesla reported $25.2 billion revenue in Q3 2024",
    text_format=FinancialData,
    temperature=0.2,
)

print(response.output_parsed)  # FinancialData(company='Tesla', revenue=25.2, quarter='Q3 2024')
```

## Response Handling

### CoT Response Structure

When a CoT completes via the finchat API, the response includes:

```python
{
    "uid": "chat-uuid",
    "message": "Final result or processing status",
    "intent": "message",  # or "loading", "error"
    "metadata": {
        "steps_params": [...],  # Step execution parameters
        "current_progress": 3,  # Current step number
        "total_progress": 5,    # Total steps
        "error": "...",         # If error occurred
        "traceback": "..."      # Error traceback if available
    },
    "children": [...]  # Child chat messages (step results)
}
```

### Error Handling

```python
def handle_cot_response(chat_data):
    """Handle CoT response with proper error checking."""
    if chat_data.get("intent") == "error":
        error_msg = chat_data.get("metadata", {}).get("error", "Unknown error")
        traceback = chat_data.get("metadata", {}).get("traceback", "")
        print(f"CoT Error: {error_msg}")
        if traceback:
            print(f"Traceback: {traceback}")
        return None
    
    return chat_data.get("message")
```

## Best Practices

1. **Use Web Search for Current Data**: Enable `enable_web_search: True` when you need real-time or current information
2. **Set Appropriate Temperature**: Use low temperature (0.1-0.2) for factual analysis, higher (0.7-0.9) for creative tasks
3. **Handle Async Execution**: CoT execution is asynchronous, always poll for results
4. **Validate Parameters**: Ensure all required CoT parameters are provided
5. **Error Handling**: Always check for errors in the response metadata
6. **Rate Limiting**: Be respectful of API rate limits when polling

## Troubleshooting

### CoT Not Found
- Verify the CoT slug exists and is correct
- Check that the CoT is not hidden (`hidden=False`)

### Parameter Errors
- Ensure all required parameters are provided
- Check parameter names match exactly (case-sensitive)
- Verify parameter format: `$param_name=value`

### Model Errors
- Verify the model name is available in l2m2
- Check l2m2 endpoint is accessible: `https://l2m2.adgo-infra.com/api/v4/chat/completions`
- Ensure API key is valid (Bearer token format)
- Set `L2M2_API_KEY` environment variable if not using default

### Timeout Issues
- Increase polling timeout
- Check if the CoT has too many steps
- Verify network connectivity to finchat instance

## Additional Resources

- **Finchat Codebase**: `/finchat/cot/methods.py` - Core CoT execution logic
- **API Endpoints**: `/finchat/api/v2/apis/cot.py` - CoT API endpoints
- **Models**: `/finchat/cot/models.py` - CoT data models
- **l2m2 Configuration**: `/finchat/core/extended_settings/l2m2.py` - l2m2 setup

## Example: Complete CoT Workflow

```python
#!/usr/bin/env python3
"""
Complete example: Call a financial analysis CoT and get results
"""

import requests
import time
import os

class FinchatCoTClient:
    def __init__(self, base_url: str, api_token: str):
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
    
    def create_session(self):
        """Create a new finchat session."""
        response = requests.post(
            f"{self.base_url}/api/v1/session/",
            headers=self.headers,
            json={}
        )
        response.raise_for_status()
        return response.json()["uid"]
    
    def execute_cot(self, session_uid: str, cot_slug: str, params: dict = None):
        """
        Execute a CoT prompt.
        
        Args:
            session_uid: Session UUID
            cot_slug: CoT slug identifier
            params: Dictionary of parameters (e.g., {"company_name": "Tesla", "quarter": "2024Q3"})
        
        Returns:
            Chat UUID for the CoT execution
        """
        # Build parameter string
        param_string = ""
        if params:
            param_string = " " + " ".join([f"${k}={v}" for k, v in params.items()])
        
        cot_message = f"/cot {cot_slug}{param_string}"
        
        # Create chat
        response = requests.post(
            f"{self.base_url}/api/v1/chat/",
            headers=self.headers,
            json={
                "session": session_uid,
                "message": cot_message,
                "analysis_model": "gemini-2.5-flash",
                "use_web_search": True
            }
        )
        response.raise_for_status()
        return response.json()["uid"]
    
    def get_chat(self, chat_uid: str):
        """Get chat details including children."""
        response = requests.get(
            f"{self.base_url}/api/v1/chat/{chat_uid}/",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def wait_for_result(self, chat_uid: str, timeout: int = 300, interval: int = 5):
        """
        Wait for CoT execution to complete.
        
        Args:
            chat_uid: Chat UUID
            timeout: Maximum seconds to wait
            interval: Seconds between polls
        
        Returns:
            Final result chat or None if timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            chat_data = self.get_chat(chat_uid)
            children = chat_data.get("children", [])
            
            if children:
                result_chat = children[-1]
                intent = result_chat.get("intent")
                
                if intent == "error":
                    error = result_chat.get("metadata", {}).get("error", "Unknown error")
                    raise Exception(f"CoT Error: {error}")
                
                if intent != "loading":
                    return result_chat
            
            time.sleep(interval)
            print(f"Waiting for CoT results... ({int(time.time() - start_time)}s elapsed)")
        
        raise TimeoutError(f"CoT execution timed out after {timeout} seconds")

# Usage example
if __name__ == "__main__":
    # Configuration
    FINCHAT_URL = os.getenv("FINCHAT_BASE_URL", "https://your-finchat-instance.com")
    API_TOKEN = os.getenv("FINCHAT_API_TOKEN", "your_token_here")
    
    # Create client
    client = FinchatCoTClient(FINCHAT_URL, API_TOKEN)
    
    # Create session
    session_uid = client.create_session()
    print(f"Created session: {session_uid}")
    
    # Execute CoT
    cot_slug = "financial-analysis"  # Replace with your CoT slug
    params = {
        "company_name": "Tesla",
        "quarter": "2024Q3"
    }
    
    chat_uid = client.execute_cot(session_uid, cot_slug, params)
    print(f"Executing CoT: {chat_uid}")
    
    # Wait for result
    try:
        result = client.wait_for_result(chat_uid, timeout=300)
        print(f"\n✅ CoT completed!")
        print(f"Result: {result['message']}")
        
        # Print metadata if available
        metadata = result.get("metadata", {})
        if metadata:
            print(f"\nMetadata: {metadata}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
```

---

**Note**: Replace all placeholder values (URLs, tokens, CoT slugs) with your actual finchat instance values.

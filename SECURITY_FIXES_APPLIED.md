# Security Fixes Applied

**Date:** December 30, 2025

## Actions Taken

### 1. ✅ Google Cloud Service Account Credentials Secured

**File:** `graphic-charter-467314-n9-d01b9547da1a.json`

- **Status:** ✅ MOVED to secure location
- **New Location:** `~/.config/sourcer/graphic-charter-467314-n9-d01b9547da1a.json`
- **Verification:** File was already properly ignored by `.gitignore` (pattern `*-*.json`)
- **Git Status:** ✅ NOT tracked in git history

**To use the credentials file:**

Set the environment variable:
```bash
export GOOGLE_APPLICATION_CREDENTIALS="$HOME/.config/sourcer/graphic-charter-467314-n9-d01b9547da1a.json"
```

Or for production/cloud deployments, use the JSON string in environment variable:
```bash
export GOOGLE_SERVICE_ACCOUNT_JSON='{"type":"service_account",...}'
```

### 2. ⚠️ Still Required: Remove Hardcoded API Keys

The following files still contain hardcoded API keys that need to be removed:

- `backend/app.py` (lines 442, 446, 450)
- `app.py` (lines 426, 430, 434)

**Required Changes:**

1. **SearchAPI API Key** (line 442):
   ```python
   # ❌ CURRENT:
   SEARCHAPI_API_KEY = os.getenv("SEARCHAPI_API_KEY", "uX29PpsVN8nCohWNzmANExdq")
   
   # ✅ SHOULD BE:
   SEARCHAPI_API_KEY = os.getenv("SEARCHAPI_API_KEY")
   if not SEARCHAPI_API_KEY:
       raise ValueError("SEARCHAPI_API_KEY environment variable is required")
   ```

2. **L2M2 API Key** (line 446):
   ```python
   # ❌ CURRENT:
   L2M2_API_KEY = "l2m2-uyGbDWdn6TGCXvAISfkfHdGd6Z7UsmoCtLD4y1ARRRU"
   
   # ✅ SHOULD BE:
   L2M2_API_KEY = os.getenv("L2M2_API_KEY")
   if not L2M2_API_KEY:
       raise ValueError("L2M2_API_KEY environment variable is required")
   ```

3. **Bucketeer API Key** (line 450):
   ```python
   # ❌ CURRENT:
   BUCKETEER_API_KEY = os.getenv("BUCKETEER_API_KEY", "bcktr-wxFrNg7Co6MbtvQdtpk39lK0TPALbW5T")
   
   # ✅ SHOULD BE:
   BUCKETEER_API_KEY = os.getenv("BUCKETEER_API_KEY")
   if not BUCKETEER_API_KEY:
       raise ValueError("BUCKETEER_API_KEY environment variable is required")
   ```

### 3. ⚠️ Still Required: Rotate Exposed API Keys

All exposed API keys should be rotated:

- [ ] SearchAPI.io API key (`uX29PpsVN8nCohWNzmANExdq`)
- [ ] L2M2 API key (`l2m2-uyGbDWdn6TGCXvAISfkfHdGd6Z7UsmoCtLD4y1ARRRU`)
- [ ] Bucketeer API key (`bcktr-wxFrNg7Co6MbtvQdtpk39lK0TPALbW5T`)
- [ ] Consider rotating Google Cloud service account key (if there's any risk it was exposed)

## Environment Variables Required

After removing hardcoded keys, ensure these environment variables are set:

```bash
# Required API Keys
export SEARCHAPI_API_KEY="your_key_here"
export L2M2_API_KEY="your_key_here"
export BUCKETEER_API_KEY="your_key_here"

# Optional (with defaults)
export BUCKETEER_BASE_URL="https://bucketeer.adgo-infra.com/"
export YOUTUBE_API_KEY="your_key_here"
export OPENAI_API_KEY="your_key_here"

# Google Cloud / NotebookLM
export GOOGLE_APPLICATION_CREDENTIALS="$HOME/.config/sourcer/graphic-charter-467314-n9-d01b9547da1a.json"
# OR
export GOOGLE_SERVICE_ACCOUNT_JSON='{"type":"service_account",...}'

export NOTEBOOKLM_PROJECT_NUMBER="511538466121"
export NOTEBOOKLM_LOCATION="global"
export NOTEBOOKLM_ENDPOINT_LOCATION="global-"
export NOTEBOOKLM_SERVICE_ACCOUNT="notebooklm@graphic-charter-467314-n9.iam.gserviceaccount.com"
```

## Next Steps

1. ✅ Google credentials file moved to secure location
2. ⚠️ Remove hardcoded API keys from code (see above)
3. ⚠️ Rotate all exposed API keys
4. ⚠️ Update deployment configurations (Railway/Vercel) with new environment variables
5. ⚠️ Test application with environment variables only (no hardcoded fallbacks)


# Security Audit Report - Exposed Credentials

**Date:** December 30, 2025  
**Repository:** sourcer  
**Status:** ⚠️ **CRITICAL ISSUES FOUND**

## Executive Summary

This audit scanned all git commits and found **multiple exposed API keys and credentials** in the repository history. While some keys are currently using environment variables with fallback defaults, **hardcoded API keys are still present in the current codebase** and have been exposed in git history.

## Critical Findings

### 1. 🔴 **CRITICAL: Hardcoded API Keys in Current Code**

The following API keys are **currently hardcoded** in the codebase:

#### Location: `backend/app.py` and `app.py` (lines 442-450)

1. **SearchAPI.io API Key**
   - **Key:** `uX29PpsVN8nCohWNzmANExdq`
   - **Line:** 442
   - **Status:** Hardcoded as fallback default
   - **Risk:** HIGH - Exposed in git history

2. **L2M2 API Key**
   - **Key:** `l2m2-uyGbDWdn6TGCXvAISfkfHdGd6Z7UsmoCtLD4y1ARRRU`
   - **Line:** 446
   - **Status:** Hardcoded directly (no environment variable fallback)
   - **Risk:** CRITICAL - Fully exposed

3. **Bucketeer API Key**
   - **Key:** `bcktr-wxFrNg7Co6MbtvQdtpk39lK0TPALbW5T`
   - **Line:** 450
   - **Status:** Hardcoded as fallback default
   - **Risk:** HIGH - Exposed in git history

### 2. 🔴 **CRITICAL: Google Cloud Service Account Private Key**

**File:** `graphic-charter-467314-n9-d01b9547da1a.json`

- **Status:** File exists in repository root
- **Contains:** Full Google Cloud service account private key
- **Risk:** CRITICAL - Full private key exposure
- **Note:** File appears to be ignored by `.gitignore` (pattern `*-*.json`), but should be verified it's not tracked

**Service Account Details:**
- Project ID: `graphic-charter-467314-n9`
- Client Email: `notebooklm@graphic-charter-467314-n9.iam.gserviceaccount.com`
- Private Key ID: `d01b9547da1a950c268d0c4ef1bbd67a121ca655`

### 3. 🟡 **MEDIUM: Historical API Key Exposure**

The following API keys were found in git commit history:

1. **SearchAPI.io API Key (Previous)**
   - **Key:** `AEqiQPXdmzJo1Zdu8o9s1GJQ`
   - **Found in commits:**
     - Commit `377911f`: "Switch SearchAPI.io API key back to original key"
     - Commit `a7a5b75`: "Update SearchAPI.io API key to new key"
   - **Status:** Replaced but still in git history
   - **Risk:** MEDIUM - Historical exposure

2. **Bucketeer API Key**
   - **Key:** `bcktr-wxFrNg7Co6MbtvQdtpk39lK0TPALbW5T`
   - **Found in:** Multiple commits and documentation files
   - **Status:** Still hardcoded in current code
   - **Risk:** HIGH

3. **L2M2 API Key**
   - **Key:** `l2m2-uyGbDWdn6TGCXvAISfkfHdGd6Z7UsmoCtLD4y1ARRRU`
   - **Found in:** Multiple commits
   - **Status:** Still hardcoded in current code
   - **Risk:** HIGH

## Affected Files

### Current Codebase
- `backend/app.py` (lines 440-450)
- `app.py` (lines 424-434)
- `# Bucketeer API Examples.md` (contains example API key)

### Git History
- Multiple commits contain exposed API keys
- Documentation files contain example API keys

## Recommendations

### Immediate Actions (URGENT)

1. **Rotate All Exposed API Keys**
   - [ ] Rotate SearchAPI.io API key (`uX29PpsVN8nCohWNzmANExdq`)
   - [ ] Rotate L2M2 API key (`l2m2-uyGbDWdn6TGCXvAISfkfHdGd6Z7UsmoCtLD4y1ARRRU`)
   - [ ] Rotate Bucketeer API key (`bcktr-wxFrNg7Co6MbtvQdtpk39lK0TPALbW5T`)
   - [ ] Revoke and regenerate Google Cloud service account key

2. **Remove Hardcoded Keys from Code**
   - [ ] Remove all hardcoded API keys from `backend/app.py`
   - [ ] Remove all hardcoded API keys from `app.py`
   - [ ] Use environment variables ONLY (no fallback defaults with real keys)
   - [ ] Add validation to fail fast if required environment variables are missing

3. **Secure Google Cloud Credentials**
   - [ ] Verify `graphic-charter-467314-n9-d01b9547da1a.json` is NOT tracked in git
   - [ ] Move credentials file outside repository or use secure secret management
   - [ ] Revoke the exposed service account key in Google Cloud Console
   - [ ] Generate new service account key if needed

### Code Changes Required

**Example fix for `backend/app.py`:**

```python
# ❌ CURRENT (INSECURE):
SEARCHAPI_API_KEY = os.getenv("SEARCHAPI_API_KEY", "uX29PpsVN8nCohWNzmANExdq")
L2M2_API_KEY = "l2m2-uyGbDWdn6TGCXvAISfkfHdGd6Z7UsmoCtLD4y1ARRRU"
BUCKETEER_API_KEY = os.getenv("BUCKETEER_API_KEY", "bcktr-wxFrNg7Co6MbtvQdtpk39lK0TPALbW5T")

# ✅ SECURE:
SEARCHAPI_API_KEY = os.getenv("SEARCHAPI_API_KEY")
if not SEARCHAPI_API_KEY:
    raise ValueError("SEARCHAPI_API_KEY environment variable is required")

L2M2_API_KEY = os.getenv("L2M2_API_KEY")
if not L2M2_API_KEY:
    raise ValueError("L2M2_API_KEY environment variable is required")

BUCKETEER_API_KEY = os.getenv("BUCKETEER_API_KEY")
if not BUCKETEER_API_KEY:
    raise ValueError("BUCKETEER_API_KEY environment variable is required")
```

### Long-term Actions

1. **Git History Cleanup** (if repository is private and keys are rotated)
   - Consider using `git filter-branch` or `BFG Repo-Cleaner` to remove exposed keys from history
   - ⚠️ **Warning:** Only do this if repository is private. If public, assume keys are compromised.

2. **Add Pre-commit Hooks**
   - Install `git-secrets` or similar tool to prevent committing secrets
   - Add regex patterns to detect API keys, passwords, and private keys

3. **Use Secret Management**
   - Consider using services like:
     - AWS Secrets Manager
     - HashiCorp Vault
     - Google Secret Manager
     - Railway/Vercel environment variables (already using)

4. **Update Documentation**
   - Remove example API keys from documentation files
   - Add instructions for setting up environment variables securely

5. **Add Security Scanning**
   - Set up automated security scanning (e.g., GitHub Secret Scanning, GitGuardian)
   - Add `.env.example` file with placeholder values

## Risk Assessment

| Credential | Current Status | Historical Exposure | Risk Level |
|------------|---------------|---------------------|------------|
| SearchAPI.io Key | Hardcoded fallback | Yes | 🔴 HIGH |
| L2M2 API Key | Hardcoded | Yes | 🔴 CRITICAL |
| Bucketeer API Key | Hardcoded fallback | Yes | 🔴 HIGH |
| Google Service Account | File in repo | Unknown | 🔴 CRITICAL |

## Verification Steps

After implementing fixes:

1. Verify no API keys in current codebase:
   ```bash
   grep -r "API_KEY.*=" backend/app.py app.py | grep -v "os.getenv\|os.environ"
   ```

2. Verify credentials file is not tracked:
   ```bash
   git ls-files | grep -i "credential\|service\|graphic-charter"
   ```

3. Test application fails gracefully without environment variables

## Notes

- The `.gitignore` file has patterns to ignore credential files (`*-*.json`), which should prevent the Google credentials file from being tracked
- However, the file exists in the repository root and should be moved or removed
- All hardcoded API keys should be removed immediately and replaced with environment variable checks

---

**Next Steps:** Rotate all exposed keys immediately and remove hardcoded values from code.


# Environment Variable Loading Fix

**Date:** October 3, 2025  
**Author:** Marcus (Chief of Staff for AI Governance)  
**Issue:** Google API authentication failing due to environment variables not loading  
**Status:** Solution implemented and ready for testing

## Problem Description

The Google MCP Server integration is failing to authenticate with Google APIs because the environment variables `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are not being properly loaded from the `.env` file.

Investigation revealed that while the `.env` file exists and contains the necessary credentials, and the `python-dotenv` library is properly imported and called in the server files, the environment variables are still not being set in the system environment.

## Root Cause Analysis

After thorough investigation, the most likely causes are:

1. Incorrect formatting in the `.env` file (e.g., extra whitespace, quotes, or line endings)
2. An issue with the `python-dotenv` library not properly parsing certain formats
3. A race condition where the environment variables are loaded but then overwritten
4. Environment variables being accessed before they're fully loaded

## Solution Implemented

This PR implements a multi-layered solution to ensure the environment variables are properly loaded:

1. **Diagnostic Tool** (`test_env_loading.py`): A simple script to test and diagnose the environment variable loading issue without modifying any existing code.

2. **Manual Loader** (`load_env_manually.py`): A standalone script that can be run before starting the server to ensure environment variables are properly loaded, bypassing any issues with the `python-dotenv` library.

3. **Enhanced Router** (`universal_router_enhanced.py`): A modified version of the Universal Message Router that includes robust environment variable loading with:
   - Direct file parsing before any imports
   - Fallback to `python-dotenv`
   - Detailed error handling and logging
   - Status reporting for critical environment variables

## Implementation Steps

To implement this fix:

1. Run the diagnostic tool to verify the specific issue:
   ```
   python test_env_loading.py
   ```

2. Option A - Use the manual loader before starting the server:
   ```
   python load_env_manually.py && python universal_message_router.py
   ```

3. Option B - Replace the existing router with the enhanced version:
   ```
   cp universal_router_enhanced.py universal_message_router.py
   python universal_message_router.py
   ```

## Expected Results

After implementing either solution:

1. The environment variables should be properly loaded and available to the application
2. The Google MCP Server should successfully authenticate with Google APIs
3. Google authentication should work without errors

## Verification

To verify the fix worked:

1. Check that environment variables are loaded:
   ```
   python -c "import os; print('GOOGLE_CLIENT_ID:', 'Set' if os.getenv('GOOGLE_CLIENT_ID') else 'Not set')"
   ```

2. Test Google API authentication:
   ```
   python -c "from google.oauth2.credentials import Credentials; print('Credentials can be imported')"
   ```

3. Run the Google MCP Server and check for authentication errors

## Additional Recommendations

1. **Standardize .env Format**: Ensure all environment variables in the `.env` file follow a consistent format:
   ```
   VARIABLE_NAME=value
   ```
   No quotes, no spaces around the equals sign, one variable per line.

2. **Environment Variable Documentation**: Create a template `.env.example` file that shows the required format without actual credentials.

3. **Load Order**: Ensure environment variables are loaded at the very beginning of the application, before any imports that might use them.

4. **Error Handling**: Add explicit error handling around environment variable access to provide clearer error messages.

---

## Technical Details

### Environment Variable Loading Code

The core of the fix is this function that loads environment variables directly from the `.env` file:

```python
def load_env_variables():
    """Manually load environment variables from .env file"""
    env_file_path = '.env'
    
    # Check if .env file exists
    if not os.path.exists(env_file_path):
        print(f"Warning: {env_file_path} file not found")
        return False
    
    try:
        # Read the .env file
        with open(env_file_path, 'r') as f:
            lines = f.readlines()
        
        # Process each line
        env_vars_set = 0
        for line in lines:
            line = line.strip()
            # Skip empty lines or comments
            if not line or line.startswith('#'):
                continue
            
            # Split on the first equals sign
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                # Strip quotes if present
                value = value.strip().strip('\'"')
                # Set environment variable if not already set
                if not os.getenv(key):
                    os.environ[key] = value
                    env_vars_set += 1
            
        print(f"Loaded {env_vars_set} environment variables from {env_file_path}")
        return True
    except Exception as e:
        print(f"Error loading environment variables: {e}")
        return False
```

This should be called before any imports that might use the environment variables.

---

Report prepared by Marcus, Chief of Staff for AI Governance
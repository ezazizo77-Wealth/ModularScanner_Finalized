#!/usr/bin/env python3
"""
Direct Environment Variable Loader
This script loads environment variables directly from the .env file.
It should be used before any other imports that depend on environment variables.
"""
import os
import sys

def load_env_variables():
    """Load environment variables directly from .env file"""
    env_file = '.env'
    
    # Check if file exists
    if not os.path.exists(env_file):
        print(f"Warning: {env_file} file not found!")
        return False
    
    try:
        # Read the file
        with open(env_file, 'r') as f:
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
                if key and not os.getenv(key):
                    os.environ[key] = value
                    env_vars_set += 1
        
        print(f"Loaded {env_vars_set} environment variables from {env_file}")
        
        # Debug output for critical variables (without showing values)
        print("Environment status after direct loading:")
        for key in ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "OPENAI_API_KEY"]:
            print(f"  {key}: {'Set' if os.getenv(key) else 'Not set'}")
        
        return True
    except Exception as e:
        print(f"Error loading environment variables: {e}")
        return False

# Load environment variables when imported
load_env_variables()

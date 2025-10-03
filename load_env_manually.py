#!/usr/bin/env python3
"""
Manual environment variable loader for Google MCP Server
This script directly loads environment variables from .env file and sets them
in the environment, bypassing any issues with python-dotenv.
"""

import os
import sys

def load_env_file():
    """Load environment variables from .env file manually"""
    print("Loading environment variables manually...")
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("Error: .env file not found!")
        return False
    
    try:
        # Read the .env file
        with open('.env', 'r') as f:
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
                # Strip quotes if present
                value = value.strip('\'"')
                # Set environment variable
                os.environ[key] = value
                env_vars_set += 1
                print(f"Set environment variable: {key}")
            else:
                print(f"Warning: Invalid line in .env file: {line}")
        
        print(f"Successfully loaded {env_vars_set} environment variables")
        return True
    
    except Exception as e:
        print(f"Error loading environment variables: {e}")
        return False

if __name__ == "__main__":
    # Run as a standalone script
    success = load_env_file()
    print("Environment variables loaded:", "Successfully" if success else "Failed")
    
    # Print status of specific variables (without values)
    print("GOOGLE_CLIENT_ID:", "Set" if "GOOGLE_CLIENT_ID" in os.environ else "Not set")
    print("GOOGLE_CLIENT_SECRET:", "Set" if "GOOGLE_CLIENT_SECRET" in os.environ else "Not set")
    print("OPENAI_API_KEY:", "Set" if "OPENAI_API_KEY" in os.environ else "Not set")

#!/usr/bin/env python3
"""
Test environment variable loading from .env file
"""

import os
from dotenv import load_dotenv

def test_env_loading():
    print("Testing .env file loading...")
    # Check if .env file exists
    print(f".env file exists: {os.path.exists('.env')}")
    
    # Try to load environment variables
    print("Loading environment variables with dotenv...")
    load_dotenv()
    
    # Check if environment variables are loaded
    google_client_id = os.getenv("GOOGLE_CLIENT_ID")
    google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    
    print(f"GOOGLE_CLIENT_ID loaded: {'Yes' if google_client_id else 'No'}")
    print(f"GOOGLE_CLIENT_SECRET loaded: {'Yes' if google_client_secret else 'No'}")
    
    # Print actual content of .env file (without revealing sensitive info)
    print("\nReading .env file content format (not showing actual values):")
    try:
        with open('.env', 'r') as f:
            lines = f.readlines()
            for line in lines:
                if '=' in line:
                    var_name, var_value = line.split('=', 1)
                    print(f"Variable: {var_name} = [value hidden]")
                else:
                    print(f"Line without '=': {line}")
    except Exception as e:
        print(f"Error reading .env file: {e}")
    
    return "Environment test completed"

if __name__ == "__main__":
    test_env_loading()

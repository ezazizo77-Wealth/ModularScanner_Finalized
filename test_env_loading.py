#!/usr/bin/env python3
"""
Test script to verify that environment variables are loaded correctly
"""
import os

# Try to load variables using our custom loader first
print("Step 1: Testing direct environment loader...")
import load_env_variables

# Check if variables are now available
print("\nStep 2: Checking environment variables after direct loading:")
for key in ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "OPENAI_API_KEY"]:
    value = os.getenv(key)
    print(f"  {key}: {'Set' if value else 'Not set'}")

# Now try standard dotenv loading as a fallback
print("\nStep 3: Testing python-dotenv loader...")
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("  dotenv loading complete")
except ImportError:
    print("  Warning: python-dotenv not installed")

# Check if variables are now available after both methods
print("\nStep 4: Final environment variable status:")
for key in ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "OPENAI_API_KEY"]:
    value = os.getenv(key)
    print(f"  {key}: {'Set' if value else 'Not set'}")

print("\nTest complete.")

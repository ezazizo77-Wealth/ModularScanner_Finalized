#!/usr/bin/env python3
"""
Test script to verify environment variable loading
"""
import os

# Print initial state
print("Initial environment variable status:")
for key in ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "OPENAI_API_KEY"]:
    print(f"  {key}: {'Set' if os.getenv(key) else 'Not set'}")

# Import our direct loader
print("\nTesting direct environment loader...")
import load_env_variables

# Check if variables are now available
print("\nEnvironment variables after direct loading:")
for key in ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "OPENAI_API_KEY"]:
    value = os.getenv(key)
    print(f"  {key}: {'Set' if value else 'Not set'}")

# Now try python-dotenv for comparison
print("\nTesting python-dotenv loader...")
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("  dotenv loading complete")
except ImportError:
    print("  Warning: python-dotenv not installed")

# Final check
print("\nFinal environment variable status:")
for key in ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "OPENAI_API_KEY"]:
    value = os.getenv(key)
    print(f"  {key}: {'Set' if value else 'Not set'}")

print("\nTest complete.")

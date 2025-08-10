"""
Debug script to check Railway environment variables
"""
import os

print("=== RAILWAY ENVIRONMENT DEBUG ===")
print(f"DATABASE_URL: {os.environ.get('DATABASE_URL', 'NOT SET')}")
print(f"PORT: {os.environ.get('PORT', 'NOT SET')}")
print(f"RAILWAY_ENVIRONMENT: {os.environ.get('RAILWAY_ENVIRONMENT', 'NOT SET')}")

print("\n=== ALL ENVIRONMENT VARIABLES ===")
for key, value in sorted(os.environ.items()):
    if any(keyword in key.upper() for keyword in ['DATABASE', 'POSTGRES', 'RAILWAY', 'PORT']):
        if 'PASSWORD' in key.upper():
            print(f"{key}: ***HIDDEN***")
        else:
            print(f"{key}: {value}")

print("\n=== END DEBUG ===")
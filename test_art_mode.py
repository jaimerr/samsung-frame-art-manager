#!/usr/bin/env python3
"""Test Art Mode features"""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from samsungtvws import SamsungTVWS

tv_ip = "192.168.1.55"
token_file = "tv_token.txt"

print(f"Connecting to {tv_ip}...")

tv = SamsungTVWS(
    host=tv_ip,
    port=8002,
    token_file=token_file,
    timeout=60,
    name="FrameArtManager"
)

tv.open()
print("✓ Connected!")

# Check token
if os.path.exists(token_file):
    with open(token_file) as f:
        print(f"Token saved: {f.read().strip()[:30]}...")

# Test Art Mode
print("\n--- Art Mode Tests ---")
art = tv.art()

# Check if supported
print("1. Checking Art Mode support...")
try:
    supported = art.supported()
    print(f"   Art Mode supported: {supported}")
except Exception as e:
    print(f"   Error: {e}")

# Get art mode status
print("2. Getting Art Mode status...")
try:
    status = art.get_artmode()
    print(f"   Art Mode status: {status}")
except Exception as e:
    print(f"   Error: {e}")

# List available art
print("3. Listing My Photos...")
try:
    photos = art.available("MY-C0004")
    print(f"   Found {len(photos) if photos else 0} photos")
    if photos:
        for p in photos[:5]:
            print(f"   - {p.get('content_id', 'unknown')[:40]}...")
except Exception as e:
    print(f"   Error: {e}")

# Get current art
print("4. Getting current artwork...")
try:
    current = art.get_current()
    print(f"   Current: {current}")
except Exception as e:
    print(f"   Error: {e}")

tv.close()
print("\n✓ All tests complete!")

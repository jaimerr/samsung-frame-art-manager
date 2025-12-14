#!/usr/bin/env python3
"""Test with WSS (secure) connection"""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from samsungtvws import SamsungTVWS

tv_ip = "192.168.1.55"
token_file = "tv_token.txt"

print(f"Trying secure connection to {tv_ip}...")

# Try with port 8002 (WSS)
try:
    tv = SamsungTVWS(
        host=tv_ip,
        port=8002,
        token_file=token_file,
        timeout=60,  # Very long timeout
        name="FrameArtManager"
    )
    
    print("Opening connection... (approve on TV if prompted)")
    tv.open()
    print("✓ Connected!")
    
    # Try to get device info
    print("Getting device info...")
    info = tv.rest_device_info()
    print(f"Device: {info}")
    
except Exception as e:
    print(f"Error: {e}")
    print(f"Type: {type(e)}")

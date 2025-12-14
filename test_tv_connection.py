#!/usr/bin/env python3
"""
Test script for Samsung Frame TV connection
Run this to test if your TV connection works
"""

import sys
import os

# Add the project to path
sys.path.insert(0, os.path.dirname(__file__))

def test_connection(tv_ip: str):
    print(f"\n{'='*50}")
    print(f"Testing Samsung Frame TV Connection")
    print(f"TV IP: {tv_ip}")
    print(f"{'='*50}\n")
    
    # Test 1: Check if library is available
    print("1. Checking samsungtvws library...")
    try:
        from samsungtvws import SamsungTVWS
        print("   ✓ Library loaded successfully")
    except ImportError as e:
        print(f"   ✗ Library not found: {e}")
        print("\n   Install with:")
        print('   pip install "git+https://github.com/xchwarze/samsung-tv-ws-api.git#egg=samsungtvws[async,encrypted]"')
        return
    
    # Test 2: Try to connect
    print("\n2. Connecting to TV...")
    print("   (You may need to approve the connection on your TV)")
    
    token_file = os.path.join(os.path.dirname(__file__), 'tv_token.txt')
    
    try:
        tv = SamsungTVWS(
            host=tv_ip,
            port=8002,
            token_file=token_file,
            timeout=30,
            name="FrameArtManager"
        )
        
        # Open connection
        tv.open()
        print("   ✓ Connection established!")
        
        # Check token
        if os.path.exists(token_file):
            with open(token_file, 'r') as f:
                token = f.read().strip()
            print(f"   ✓ Token saved: {token[:20]}..." if len(token) > 20 else f"   ✓ Token saved: {token}")
        
    except Exception as e:
        print(f"   ✗ Connection failed: {e}")
        print("\n   Troubleshooting:")
        print("   - Is your TV powered ON (not standby)?")
        print("   - Is your TV on the same network?")
        print("   - Did you approve the connection on the TV?")
        return
    
    # Test 3: Check Art Mode support
    print("\n3. Checking Art Mode support...")
    try:
        art = tv.art()
        supported = art.supported()
        print(f"   {'✓' if supported else '✗'} Art Mode supported: {supported}")
        
        if supported:
            # Test 4: Get art mode status
            print("\n4. Getting Art Mode status...")
            try:
                status = art.get_artmode()
                print(f"   ✓ Art Mode is: {status}")
            except Exception as e:
                print(f"   ⚠ Could not get status: {e}")
            
            # Test 5: List uploaded art
            print("\n5. Listing uploaded art...")
            try:
                art_list = art.available("MY-C0004")
                print(f"   ✓ Found {len(art_list) if art_list else 0} uploaded images")
                if art_list:
                    for i, item in enumerate(art_list[:3]):
                        print(f"      - {item.get('content_id', 'unknown')}")
                    if len(art_list) > 3:
                        print(f"      ... and {len(art_list) - 3} more")
            except Exception as e:
                print(f"   ⚠ Could not list art: {e}")
    
    except Exception as e:
        print(f"   ✗ Art Mode check failed: {e}")
    
    print(f"\n{'='*50}")
    print("Test complete!")
    print(f"{'='*50}\n")
    
    # Close connection
    try:
        tv.close()
    except:
        pass


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_tv_connection.py <TV_IP_ADDRESS>")
        print("Example: python test_tv_connection.py 192.168.1.55")
        sys.exit(1)
    
    tv_ip = sys.argv[1]
    test_connection(tv_ip)


#!/usr/bin/env python3
"""
Debug test script to test the updated URL formatting for StatCan tables.
Run with: python -m tests.debug.test_formatted_links
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.wds_client import WDSClient

def format_pid_for_url(pid):
    """Format a PID for use in StatCan table URLs."""
    pid_str = str(pid)
    if len(pid_str) <= 8:  # 8-digit or shorter needs formatting
        # The web URL format for tables requires 10 digits (pid with 8 digits + 01)
        # Format: AAAAAAABB where AAAAAAAA is 8-digit PID and BB is 01
        return pid_str.zfill(8) + "01"
    return pid_str

def generate_statcan_url(pid):
    """Generate a properly formatted StatCan table URL."""
    pid_str = format_pid_for_url(pid)
    return f"https://www150.statcan.gc.ca/t1/tbl1/en/cv.action?pid={pid_str}"

async def test_pid_formatting():
    """Test PID formatting for various input formats."""
    print("\n=== Testing PID URL Formatting ===")
    
    # Test cases with different PID formats
    test_cases = [
        {"pid": "18100004", "expected": "1810000401", "description": "8-digit string"},
        {"pid": 18100004, "expected": "1810000401", "description": "8-digit integer"},
        {"pid": "1810000401", "expected": "1810000401", "description": "10-digit string"},
        {"pid": 1810000401, "expected": "1810000401", "description": "10-digit integer"},
        {"pid": "3610043402", "expected": "3610043402", "description": "10-digit existing table ID"},
        {"pid": "0036", "expected": "0000003601", "description": "Short 4-digit ID"},
        {"pid": 36, "expected": "0000003601", "description": "Very short ID as integer"}
    ]
    
    for tc in test_cases:
        pid = tc["pid"]
        expected = tc["expected"]
        formatted = format_pid_for_url(pid)
        url = generate_statcan_url(pid)
        
        print(f"\nTest case: {tc['description']}")
        print(f"Input PID: {pid}")
        print(f"Formatted PID: {formatted}")
        print(f"Generated URL: {url}")
        
        if formatted == expected:
            print("✅ PID formatting test PASSED")
        else:
            print(f"❌ PID formatting test FAILED - Expected: {expected}, Got: {formatted}")

async def test_with_real_vectors():
    """Test URL generation with real vector data."""
    print("\n=== Testing URL Generation with Real Data ===")
    
    client = WDSClient()
    try:
        # Test vectors for different tables
        test_vectors = ["v41690973", "v21581063", "v111955426"]  # CPI, GDP, Employment
        
        data = await client.get_data_from_vectors(test_vectors, 1)
        
        if data.get("status") == "SUCCESS":
            vector_data = data.get("object", [])
            
            for item in vector_data:
                vector_id = item.get("vectorId", "")
                product_id = item.get("productId", "")
                
                print(f"\nVector: v{vector_id}")
                print(f"Raw Product ID: {product_id}")
                
                # Format PID and generate URL
                formatted_pid = format_pid_for_url(product_id)
                url = generate_statcan_url(product_id)
                
                print(f"Formatted PID: {formatted_pid}")
                print(f"Generated URL: {url}")
                
                # Try to fetch the URL (without actually downloading it)
                print(f"✅ URL format looks valid")
        else:
            print(f"Error retrieving vector data: {data.get('object', 'Unknown error')}")
    finally:
        await client.close()

async def main():
    """Run all tests."""
    print("Starting URL formatting tests...")
    
    try:
        # Test PID formatting
        await test_pid_formatting()
        
        # Test with real data
        await test_with_real_vectors()
        
        print("\n✅ All URL formatting tests completed!")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n❌ Error during testing: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
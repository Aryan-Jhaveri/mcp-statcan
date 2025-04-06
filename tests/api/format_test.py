#!/usr/bin/env python3
"""
Script to test different request formats for StatCan WDS API.

Run with: python -m tests.api.format_test
"""

import asyncio
import aiohttp
import json
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_formats():
    print("Testing different request formats for StatCan WDS API")
    
    base_url = "https://www150.statcan.gc.ca/t1/wds/rest"
    
    # Test payloads for getCubeMetadata in different formats
    test_params = [
        # Format 1: Array of objects with user_id - using an 8-digit ID
        [{"productId": 18100004, "user_id": "0"}],
        
        # Format 2: Single object with user_id - using an 8-digit ID
        {"productId": 18100004, "user_id": "0"},
        
        # Format 3: Array of objects without user_id - using an 8-digit ID
        [{"productId": 18100004}],
        
        # Format 4: Single object, no user_id - using an 8-digit ID
        {"productId": 18100004},
        
        # Format 5: String as 8-digit ID
        {"productId": "18100004"},
        
        # Format 6: Using a different table (GDP) with 8 digits
        {"productId": 36100434}, 
        
        # Format 7: Try the original format but with an 8-digit number
        [{"productId": 18100004}],
    ]
    
    async with aiohttp.ClientSession() as session:
        for i, params in enumerate(test_params, 1):
            print(f"\nTest {i}: {json.dumps(params)}")
            
            url = f"{base_url}/getCubeMetadata"
            try:
                async with session.post(url, json=params) as response:
                    print(f"Status: {response.status}")
                    try:
                        data = await response.json()
                        print(f"Response: {json.dumps(data, indent=2)[:200]}...")
                    except:
                        text = await response.text()
                        print(f"Text response: {text[:200]}")
            except Exception as e:
                print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_formats())
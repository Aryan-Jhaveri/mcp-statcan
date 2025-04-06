#!/usr/bin/env python3
"""
Script to directly test StatCan API endpoints without our client.

Run with: python -m examples.direct_api_test
"""

import asyncio
import aiohttp
import json
import sys
from datetime import datetime, timedelta

async def test_api_endpoints():
    print("Testing StatCan WDS API endpoints directly...")
    
    # Use a direct URL from documentation
    base_url = "https://www150.statcan.gc.ca/t1/wds/rest"
    
    async with aiohttp.ClientSession() as session:
        # Test 1: Try getting changed cube list with a date
        today = datetime.now().strftime("%Y-%m-%d")
        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        
        print(f"\n1. Testing getChangedCubeList/{week_ago}...")
        url = f"{base_url}/getChangedCubeList/{week_ago}"
        try:
            async with session.get(url) as response:
                print(f"Status: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    print(f"Response: {json.dumps(data, indent=2)[:500]}...") 
                else:
                    text = await response.text()
                    print(f"Error: {text[:200]}")
        except Exception as e:
            print(f"Error: {e}")
        
        # Test 2: Try getting cube metadata with POST
        print("\n2. Testing getCubeMetadata...")
        url = f"{base_url}/getCubeMetadata"
        try:
            # CPI table
            data = {"productId": "1810000401"}
            async with session.post(url, json=data) as response:
                print(f"Status: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    print(f"Response: {json.dumps(data, indent=2)[:500]}...") 
                else:
                    text = await response.text()
                    print(f"Error: {text[:200]}")
        except Exception as e:
            print(f"Error: {e}")
        
        # Test 3: Try vector data with POST
        print("\n3. Testing getDataFromVectorsAndLatestNPeriods...")
        url = f"{base_url}/getDataFromVectorsAndLatestNPeriods"
        try:
            data = {"vectors": ["v41690973"], "latestN": 5}
            async with session.post(url, json=data) as response:
                print(f"Status: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    print(f"Response: {json.dumps(data, indent=2)[:500]}...") 
                else:
                    text = await response.text()
                    print(f"Error: {text[:200]}")
        except Exception as e:
            print(f"Error: {e}")
        
        # Test 4: Try getAllCubesList
        print("\n4. Testing getAllCubesList...")
        url = f"{base_url}/getAllCubesList"
        try:
            async with session.get(url) as response:
                print(f"Status: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    print(f"Response: {json.dumps(data, indent=2)[:500]}...") 
                else:
                    text = await response.text()
                    print(f"Error: {text[:200]}")
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_api_endpoints())
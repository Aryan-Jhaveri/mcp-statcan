#!/usr/bin/env python3
"""
Test using array format for StatCan WDS API as specified in the user guide.
"""

import asyncio
import aiohttp
import json
import sys

async def test_with_array_format():
    """Test StatCan WDS API using array format in payload."""
    base_url = "https://www150.statcan.gc.ca/t1/wds/rest"
    
    # Headers based on the user guide
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    test_cases = [
        {
            "name": "Get CPI data with array format",
            "endpoint": "getDataFromVectorsAndLatestNPeriods",
            "payload": [{"vectorId": "v41690973", "latestN": 5}]
        },
        {
            "name": "Get CPI cube metadata with array format",
            "endpoint": "getCubeMetadata",
            "payload": [{"productId": "18100004"}]
        },
        {
            "name": "Get code sets",
            "endpoint": "getCodeSets",
            "payload": [],
            "use_get": True
        },
        {
            "name": "Get series info with array format",
            "endpoint": "getSeriesInfoFromVector",
            "payload": [{"vectorId": "v41690973"}]
        }
    ]
    
    async with aiohttp.ClientSession() as session:
        for test in test_cases:
            print(f"\n===== Testing {test['name']} =====")
            url = f"{base_url}/{test['endpoint']}"
            print(f"URL: {url}")
            print(f"Payload: {json.dumps(test['payload'])}")
            
            try:
                if test.get("use_get", False):
                    async with session.get(url, headers=headers) as response:
                        print(f"Status: {response.status}")
                        try:
                            data = await response.json()
                            print(f"Response (first 500 chars): {json.dumps(data)[:500]}")
                        except:
                            text = await response.text()
                            print(f"Text response (first 200 chars): {text[:200]}")
                else:
                    async with session.post(url, json=test['payload'], headers=headers) as response:
                        print(f"Status: {response.status}")
                        try:
                            data = await response.json()
                            print(f"Response (first 500 chars): {json.dumps(data)[:500]}")
                        except:
                            text = await response.text()
                            print(f"Text response (first 200 chars): {text[:200]}")
            except Exception as e:
                print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_with_array_format())
#!/usr/bin/env python3
"""
Test using formats exactly as specified in the official StatCan WDS API user guide.
"""

import asyncio
import aiohttp
import json
import sys

async def test_with_official_formats():
    """Test StatCan WDS API using formats from the user guide."""
    base_url = "https://www150.statcan.gc.ca/t1/wds/rest"
    
    # Headers required by the API
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    # Test cases exactly as shown in the user guide
    test_cases = [
        {
            "name": "Get CPI data with proper format",
            "endpoint": "getDataFromVectorsAndLatestNPeriods",
            "payload": {"vectors": ["v41690973"], "latestN": 5, "user_id": "0"}
        },
        {
            "name": "Get CPI cube metadata",
            "endpoint": "getCubeMetadata",
            "payload": {"productId": "18100004", "user_id": "0"}
        },
        {
            "name": "Get CPI cube metadata (numeric productId)",
            "endpoint": "getCubeMetadata",
            "payload": {"productId": 18100004, "user_id": "0"}
        },
        {
            "name": "Get series info for CPI",
            "endpoint": "getSeriesInfoFromVector",
            "payload": {"vectorId": "v41690973", "user_id": "0"}
        },
        {
            "name": "Get data from cube coordinate",
            "endpoint": "getDataFromCubePidCoord",
            "payload": {"productId": "18100004", "coordinate": ["1.1.1", "1.1"], "latestN": 5, "user_id": "0"}
        },
        {
            "name": "Get series info from cube coordinate",
            "endpoint": "getSeriesInfoFromCubePidCoord",
            "payload": {"productId": "18100004", "coordinate": ["1.1.1", "1.1"], "user_id": "0"}
        }
    ]
    
    async with aiohttp.ClientSession() as session:
        for test in test_cases:
            print(f"\n===== Testing {test['name']} =====")
            url = f"{base_url}/{test['endpoint']}"
            print(f"URL: {url}")
            print(f"Payload: {json.dumps(test['payload'])}")
            
            try:
                async with session.post(url, json=test['payload'], headers=headers) as response:
                    print(f"Status: {response.status}")
                    try:
                        data = await response.json()
                        if isinstance(data, list) and len(data) > 0:
                            print(f"Response (array, first item): {json.dumps(data[0])[:500]}")
                        else:
                            print(f"Response (first 500 chars): {json.dumps(data)[:500]}")
                    except:
                        text = await response.text()
                        print(f"Text response (first 200 chars): {text[:200]}")
            except Exception as e:
                print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_with_official_formats())
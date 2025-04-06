#!/usr/bin/env python3
"""
Script to test different vector data request formats for StatCan WDS API.

Run with: python scripts/vector_test.py
"""

import asyncio
import aiohttp
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_vector_formats():
    print("Testing different vector data request formats for StatCan WDS API")
    
    base_url = "https://www150.statcan.gc.ca/t1/wds/rest"
    
    # Test payloads for getDataFromVectorsAndLatestNPeriods
    vector_test_params = [
        # Format 1: Array of objects with vector info
        [{"vectorId": "v41690973", "latestN": 3}],
        
        # Format 2: Single object with vectors as array
        {"vectors": ["v41690973"], "latestN": 3},
        
        # Format 3: Object with a single vector
        {"vectorId": "v41690973", "latestN": 3},
        
        # Format 4: Array of objects, numeric vector ID
        [{"vectorId": 41690973, "latestN": 3}],
        
        # Format 5: Vector without v prefix
        [{"vectorId": "41690973", "latestN": 3}]
    ]
    
    async with aiohttp.ClientSession() as session:
        for i, params in enumerate(vector_test_params, 1):
            print(f"\nVector Test {i}: {json.dumps(params)}")
            
            url = f"{base_url}/getDataFromVectorsAndLatestNPeriods"
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
                
    # Test payload for getSeriesInfoFromVector
    series_test_params = [
        # Format 1: Array of objects
        [{"vectorId": "v41690973"}],
        
        # Format 2: Single object
        {"vectorId": "v41690973"},
        
        # Format 3: Array of objects without v prefix
        [{"vectorId": 41690973}],
        
        # Format 4: ID as string without v
        [{"vectorId": "41690973"}]
    ]
    
    print("\n\nTesting getSeriesInfoFromVector endpoint:")
    async with aiohttp.ClientSession() as session:
        for i, params in enumerate(series_test_params, 1):
            print(f"\nSeries Test {i}: {json.dumps(params)}")
            
            url = f"{base_url}/getSeriesInfoFromVector"
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
    asyncio.run(test_vector_formats())
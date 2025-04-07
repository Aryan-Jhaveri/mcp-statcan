#!/usr/bin/env python3
"""
Direct test of StatCan WDS API endpoints with proper headers.
"""

import asyncio
import aiohttp
import json
import sys
from pathlib import Path

# Base URL for the StatCan WDS API
BASE_URL = "https://www150.statcan.gc.ca/t1/wds/rest"

async def test_endpoint(session, endpoint, payload, description):
    """Test a specific API endpoint with the given payload."""
    url = f"{BASE_URL}/{endpoint}"
    
    print(f"\nTesting {endpoint}: {description}")
    print(f"Payload: {json.dumps(payload)}")
    
    # Important: Set proper headers for the request
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    try:
        async with session.post(url, json=payload, headers=headers) as response:
            print(f"Status Code: {response.status}")
            print(f"Response Headers: {response.headers}")
            
            try:
                data = await response.json()
                return {"status": response.status, "data": data}
            except:
                text = await response.text()
                print(f"Text response: {text[:200]}")
                return {"status": response.status, "text": text}
    except Exception as e:
        print(f"Error: {e}")
        return {"status": "error", "message": str(e)}

async def run_tests():
    """Run tests against various WDS API endpoints."""
    async with aiohttp.ClientSession() as session:
        # Test 1: Get all cubes list (simplest endpoint)
        print("\n===== Test 1: getAllCubesList =====")
        result = await test_endpoint(session, "getAllCubesList", {}, "Get all cubes list")
        
        # Test 2: Get cube metadata with user_id
        print("\n===== Test 2: getCubeMetadata with user_id =====")
        payload2 = {"productId": "18100004", "user_id": "0"}
        result2 = await test_endpoint(session, "getCubeMetadata", payload2, "Get CPI cube metadata")
        
        # Test 3: Get cube metadata without user_id
        print("\n===== Test 3: getCubeMetadata without user_id =====")
        payload3 = {"productId": "18100004"}
        result3 = await test_endpoint(session, "getCubeMetadata", payload3, "Get CPI cube metadata")
        
        # Test 4: Get vector data with vectorId
        print("\n===== Test 4: getDataFromVectorsAndLatestNPeriods with vectorId =====")
        payload4 = {"vectorId": "v41690973", "latestN": 5}
        result4 = await test_endpoint(session, "getDataFromVectorsAndLatestNPeriods", payload4, "Get CPI All-items data")
        
        # Test 5: Get vector data with vectorId array
        print("\n===== Test 5: getDataFromVectorsAndLatestNPeriods with vectors array =====")
        payload5 = {"vectors": ["v41690973"], "latestN": 5}
        result5 = await test_endpoint(session, "getDataFromVectorsAndLatestNPeriods", payload5, "Get CPI All-items data with vectors array")
        
        # Test 6: Get vector data with 10-digit productId
        print("\n===== Test 6: getCubeMetadata with 10-digit productId =====")
        payload6 = {"productId": "1810000401", "user_id": "0"}
        result6 = await test_endpoint(session, "getCubeMetadata", payload6, "Get CPI cube metadata with 10-digit PID")
        
        # Test 7: getSeriesInfoFromVector
        print("\n===== Test 7: getSeriesInfoFromVector =====")
        payload7 = {"vectorId": "v41690973"}
        result7 = await test_endpoint(session, "getSeriesInfoFromVector", payload7, "Get CPI All-items series info")

if __name__ == "__main__":
    asyncio.run(run_tests())
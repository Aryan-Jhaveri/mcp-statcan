#!/usr/bin/env python3
"""
Simple script to test the StatCan WDS API connection.

Run with: python scripts/test_api.py
"""

import asyncio
import sys
import os
import json
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.wds_client import WDSClient


async def test_changed_cubes():
    """Test retrieving recently changed cubes."""
    print("\n=== Testing get_changed_cube_list ===")
    client = WDSClient()
    
    try:
        print("Fetching cubes changed in the last 30 days...")
        result = await client.get_changed_cube_list(30)
        
        if result["status"] == "SUCCESS":
            cubes = result["object"]
            print(f"Retrieved {len(cubes)} cubes.")
            
            if cubes:
                print("\nFirst 3 changed cubes:")
                for i, cube in enumerate(cubes[:3]):
                    print(f"{i+1}. {cube.get('productId', 'Unknown')} - {cube.get('cubeTitleEn', 'Unknown')}")
                    print(f"   Last released: {cube.get('releaseTime', 'Unknown')}")
            else:
                print("No cubes found.")
        else:
            print(f"Error: {result.get('object', 'Unknown error')}")
    finally:
        await client.close()


async def test_cube_metadata():
    """Test retrieving metadata for specific cubes."""
    print("\n=== Testing get_cube_metadata ===")
    client = WDSClient()
    
    # PIDs from our common_tables.md
    test_pids = [
        ("1810000401", "Consumer Price Index"),
        ("3610043401", "GDP by industry"),
        ("1410028701", "Labour force characteristics")
    ]
    
    try:
        for pid, description in test_pids:
            print(f"\nFetching metadata for {description} (PID: {pid})...")
            result = await client.get_cube_metadata(pid)
            
            if result["status"] == "SUCCESS":
                metadata = result["object"]
                print(f"Title: {metadata.get('cubeTitleEn', 'Unknown')}")
                print(f"Date range: {metadata.get('cubeStartDate', 'Unknown')} to {metadata.get('cubeEndDate', 'Unknown')}")
                
                dimensions = metadata.get("dimension", [])
                print(f"Dimensions ({len(dimensions)}):")
                for i, dim in enumerate(dimensions[:3]):  # Show first 3 dimensions
                    name = dim.get('dimensionNameEn', 'Unknown')
                    members = len(dim.get('member', []))
                    print(f"  {i+1}. {name} ({members} members)")
                
                if len(dimensions) > 3:
                    print(f"  ... and {len(dimensions) - 3} more dimensions")
            else:
                print(f"Error: {result.get('object', 'Unknown error')}")
    finally:
        await client.close()


async def test_vector_data():
    """Test retrieving data for specific vectors."""
    print("\n=== Testing get_data_from_vectors ===")
    client = WDSClient()
    
    # Test vectors from our common_tables.md
    test_vectors = [
        ("v41690973", "CPI All-items, Canada"),
        ("v65201210", "GDP at basic prices, All industries"),
        ("v2062810", "Unemployment rate")
    ]
    
    try:
        for vector, description in test_vectors:
            print(f"\nFetching data for {description} (Vector: {vector})...")
            result = await client.get_data_from_vectors([vector], 5)
            
            if result["status"] == "SUCCESS":
                # The API response format varies, handle different formats
                obj = result["object"]
                
                if isinstance(obj, list) and len(obj) > 0:
                    # If it's a list, take the first element
                    data = obj[0]
                elif isinstance(obj, dict):
                    # If it's a direct dictionary
                    data = obj
                else:
                    data = None
                
                if data and "vectorDataPoint" in data:
                    print(f"Series: {data.get('SeriesTitleEn', 'Unknown')}")
                    
                    points = data.get("vectorDataPoint", [])
                    print(f"Recent data points ({len(points)} retrieved):")
                    for point in points[:5]:
                        period = point.get("refPer", "Unknown")
                        value = point.get("value", "N/A")
                        print(f"  {period}: {value}")
                else:
                    print("No data found or unexpected data format.")
            else:
                print(f"Error: {result.get('object', 'Unknown error')}")
    finally:
        await client.close()


async def test_search_cubes():
    """Test searching for cubes by keyword."""
    print("\n=== Testing search_cubes ===")
    client = WDSClient()
    
    test_searches = ["inflation", "housing", "employment"]
    
    try:
        for search_term in test_searches:
            print(f"\nSearching for cubes related to '{search_term}'...")
            result = await client.search_cubes(search_term)
            
            if result["status"] == "SUCCESS":
                cubes = result["object"]
                print(f"Found {len(cubes)} cubes matching '{search_term}'.")
                
                if cubes:
                    print("\nTop 3 matching cubes:")
                    for i, cube in enumerate(cubes[:3]):
                        print(f"{i+1}. {cube.get('productId', 'Unknown')} - {cube.get('cubeTitleEn', 'Unknown')}")
            else:
                print(f"Error: {result.get('object', 'Unknown error')}")
    finally:
        await client.close()


async def main():
    """Run all tests."""
    print("Starting StatCan WDS API tests...")
    
    try:
        await test_changed_cubes()
        await test_cube_metadata()
        await test_vector_data()
        await test_search_cubes()
        
        print("\n✅ All tests completed!")
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    # Create the scripts directory if it doesn't exist
    os.makedirs(Path(__file__).parent, exist_ok=True)
    
    # Run the tests
    sys.exit(asyncio.run(main()))
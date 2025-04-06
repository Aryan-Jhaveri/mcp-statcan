#!/usr/bin/env python3
"""
Script to test the StatCan WDS API client with the new methods.

Run with: python -m tests.api.test_api
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.wds_client import WDSClient

async def test_get_changed_cube_list():
    """Test the get_changed_cube_list method."""
    client = WDSClient()
    
    try:
        print("\n=== Testing get_changed_cube_list ===")
        result = await client.get_changed_cube_list(last_updated_days=7)
        
        assert "status" in result
        assert result["status"] == "SUCCESS"
        assert "object" in result
        
        cubes = result["object"]
        print(f"Found {len(cubes)} cubes updated in the last 7 days")
        
        # Print the first few cubes
        for i, cube in enumerate(cubes[:3], 1):
            print(f"{i}. {cube.get('productId', 'Unknown')} - {cube.get('cubeTitleEn', 'Unknown Title')}")
            
        if len(cubes) > 3:
            print(f"... and {len(cubes) - 3} more cubes")
    finally:
        await client.close()

async def test_get_cube_metadata():
    """Test the get_cube_metadata method."""
    client = WDSClient()
    
    try:
        print("\n=== Testing get_cube_metadata ===")
        # CPI Monthly (1810000401)
        pid = "1810000401"
        print(f"Getting metadata for cube {pid} (CPI Monthly)")
        
        result = await client.get_cube_metadata(pid)
        
        assert "status" in result
        assert result["status"] == "SUCCESS"
        assert "object" in result
        
        metadata = result["object"]
        print(f"Title: {metadata.get('cubeTitleEn', 'Unknown')}")
        print(f"Date Range: {metadata.get('cubeStartDate', 'Unknown')} to {metadata.get('cubeEndDate', 'Unknown')}")
        
        dimensions = metadata.get("dimension", [])
        print(f"Dimensions: {len(dimensions)}")
        
        for i, dim in enumerate(dimensions, 1):
            print(f"  {i}. {dim.get('dimensionNameEn', 'Unknown')} ({len(dim.get('member', []))} members)")
    finally:
        await client.close()

async def test_get_data_from_vectors():
    """Test the get_data_from_vectors method."""
    client = WDSClient()
    
    try:
        print("\n=== Testing get_data_from_vectors ===")
        # CPI All-items (v41690973)
        vectors = ["v41690973"]
        n_periods = 5
        print(f"Getting data for vector {vectors[0]} (CPI All-items) for {n_periods} periods")
        
        result = await client.get_data_from_vectors(vectors, n_periods)
        
        assert "status" in result
        assert result["status"] == "SUCCESS"
        assert "object" in result
        
        # Print the data
        data = result["object"]
        if isinstance(data, list) and data:
            item = data[0]
            
            vector_id = item.get("vectorId", "Unknown")
            observations = item.get("vectorDataPoint", [])
            
            print(f"Vector: {vector_id}")
            print(f"Observations: {len(observations)}")
            
            for obs in observations:
                print(f"  {obs.get('refPer', 'Unknown')}: {obs.get('value', 'N/A')}")
        else:
            print("No data returned or unexpected format")
    finally:
        await client.close()

async def test_get_series_info_from_vector():
    """Test the get_series_info_from_vector method."""
    client = WDSClient()
    
    try:
        print("\n=== Testing get_series_info_from_vector ===")
        # CPI All-items (v41690973)
        vector = "v41690973"
        print(f"Getting series info for vector {vector} (CPI All-items)")
        
        result = await client.get_series_info_from_vector(vector)
        
        assert "status" in result
        assert result["status"] == "SUCCESS"
        assert "object" in result
        
        # Print the series info
        series_info = result["object"]
        if isinstance(series_info, list) and series_info:
            info = series_info[0]
            
            print(f"Title: {info.get('SeriesTitleEn', 'Unknown')}")
            print(f"Frequency: {info.get('frequencyCode', 'Unknown')}")
            print(f"Start Date: {info.get('startDate', 'Unknown')}")
            print(f"End Date: {info.get('endDate', 'Unknown')}")
            print(f"UOM: {info.get('UOMEn', 'Unknown')}")
        else:
            print("No series info returned or unexpected format")
    finally:
        await client.close()

async def test_search_cubes():
    """Test the search_cubes method."""
    client = WDSClient()
    
    try:
        print("\n=== Testing search_cubes ===")
        search_terms = ["inflation", "housing prices", "gdp monthly"]
        
        for term in search_terms:
            print(f"\nSearching for '{term}'...")
            result = await client.search_cubes(term)
            
            assert "status" in result
            assert result["status"] == "SUCCESS"
            assert "object" in result
            
            cubes = result["object"]
            print(f"Found {len(cubes)} results")
            
            # Print the first few results
            for i, cube in enumerate(cubes[:3], 1):
                title = cube.get("cubeTitleEn", cube.get("productTitle", "Unknown"))
                pid = cube.get("productId", "Unknown")
                print(f"{i}. {title} (PID: {pid})")
            
            if len(cubes) > 3:
                print(f"... and {len(cubes) - 3} more results")
    finally:
        await client.close()

async def test_new_api_methods():
    """Test the newly added API methods."""
    client = WDSClient()
    
    try:
        print("\n=== Testing New API Methods ===")
        
        # 1. Test get_data_from_vector_by_range
        print("\n--- Testing get_data_from_vector_by_range ---")
        vector = "v41690973"  # CPI All-items
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        
        print(f"Getting data for vector {vector} from {start_date} to {end_date}")
        result = await client.get_data_from_vector_by_range(vector, start_date, end_date)
        
        if result.get("status") == "SUCCESS":
            data = result.get("object", {})
            if isinstance(data, list) and data:
                item = data[0]
                observations = item.get("vectorDataPoint", [])
                print(f"Retrieved {len(observations)} observations")
                
                # Print first 3 observations
                for i, obs in enumerate(observations[:3], 1):
                    print(f"  {i}. {obs.get('refPer', 'Unknown')}: {obs.get('value', 'N/A')}")
                
                if len(observations) > 3:
                    print(f"  ... and {len(observations) - 3} more observations")
            else:
                print("No data or unexpected format returned")
        else:
            print(f"Error: {result}")
        
        # 2. Test get_bulk_vector_data_by_range
        print("\n--- Testing get_bulk_vector_data_by_range ---")
        vectors = ["v41690973", "v41691048"]  # CPI All-items and Shelter
        
        print(f"Getting data for vectors {vectors} from {start_date} to {end_date}")
        result = await client.get_bulk_vector_data_by_range(vectors, start_date, end_date)
        
        if result.get("status") == "SUCCESS":
            data = result.get("object", [])
            print(f"Retrieved data for {len(data)} vectors")
            
            # Print information for each vector
            for i, vector_data in enumerate(data, 1):
                vector_id = vector_data.get("vectorId", "Unknown")
                observations = vector_data.get("vectorDataPoint", [])
                print(f"  Vector {i}: {vector_id} - {len(observations)} observations")
        else:
            print(f"Error: {result}")
        
        # 3. Test get_data_from_cube_coordinate
        print("\n--- Testing get_data_from_cube_coordinate ---")
        pid = "1810000401"  # CPI Monthly
        coordinate = ["1.1.1", "1.1"]  # Canada, All-items
        
        print(f"Getting data for cube {pid} with coordinate {coordinate}")
        result = await client.get_data_from_cube_coordinate(pid, coordinate, 5)
        
        if result.get("status") == "SUCCESS":
            data = result.get("object", [])
            
            if isinstance(data, list) and data:
                item = data[0]
                title = item.get("SeriesTitleEn", "Unknown Series")
                coordinate_value = item.get("coordinate", [])
                
                print(f"Retrieved coordinate data for: {title}")
                print(f"Coordinate: {coordinate_value}")
            else:
                print("Retrieved data but format not as expected")
        else:
            print(f"Error: {result}")
        
        # 4. Skip get_changed_series_list which doesn't seem to be working 
        # with the public API
        
        print("\n--- Testing get_code_sets ---")
        result = await client.get_code_sets()
        
        if result.get("status") == "SUCCESS":
            code_sets = result.get("object", {})
            print("Available code sets:")
            
            for code_set_name, codes in code_sets.items():
                if isinstance(codes, list):
                    print(f"  {code_set_name}: {len(codes)} codes")
        else:
            print(f"Error: {result}")
        
        # 5. Test get_full_table_download_url
        print("\n--- Testing get_full_table_download_url ---")
        pid = "1810000401"  # CPI Monthly
        
        url = await client.get_full_table_download_url(pid, "csv")
        print(f"CSV download URL: {url}")
        
        url = await client.get_full_table_download_url(pid, "sdmx")
        print(f"SDMX download URL: {url}")
        
        # 6. Test get_code_sets
        print("\n--- Testing get_code_sets ---")
        result = await client.get_code_sets()
        
        if result.get("status") == "SUCCESS":
            code_sets = result.get("object", {})
            print("Available code sets:")
            
            for code_set_name, codes in code_sets.items():
                print(f"  {code_set_name}: {len(codes)} codes")
        else:
            print(f"Error: {result}")
        
    finally:
        await client.close()

async def main():
    """Run all tests."""
    print("Starting StatCan WDS API client tests...")
    
    try:
        print("\n=== Testing Basic API Methods ===")
        await test_get_changed_cube_list()
        await test_get_cube_metadata()
        await test_get_data_from_vectors()
        await test_get_series_info_from_vector()
        await test_search_cubes()
        
        print("\n=== Testing New API Methods ===")
        await test_new_api_methods()
        
        print("\n✅ All API tests completed!")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n❌ Error during testing: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
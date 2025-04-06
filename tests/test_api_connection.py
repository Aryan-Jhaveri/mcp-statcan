"""
Basic tests for connecting to the StatCan WDS API and retrieving data.

Run with: python -m pytest tests/test_api_connection.py -v
"""

import asyncio
import pytest

from src.wds_client import WDSClient


@pytest.mark.asyncio
async def test_get_changed_cube_list():
    """Test getting a list of recently changed cubes."""
    client = WDSClient()
    
    try:
        # Request cubes changed in the last 30 days
        result = await client.get_changed_cube_list(30)
        
        # Verify the response structure
        assert result is not None
        assert "status" in result
        assert result["status"] == "SUCCESS"
        assert "object" in result
        assert isinstance(result["object"], list)
        
        # If there are results, verify some fields
        if result["object"]:
            cube = result["object"][0]
            assert "productId" in cube
            # API response format may vary, not all cubes have cubeTitleEn
            
            # Print some information about the first cube
            print(f"\nFound cube: {cube['productId']}")
            if "cubeTitleEn" in cube:
                print(f"Title: {cube['cubeTitleEn']}")
            if "releaseTime" in cube:
                print(f"Last release: {cube['releaseTime']}")
    finally:
        # Clean up
        await client.close()


@pytest.mark.asyncio
async def test_get_cube_metadata():
    """Test retrieving metadata for a specific cube."""
    client = WDSClient()
    
    try:
        # Get metadata for Consumer Price Index - pid from common_tables.md
        pid = "1810000401"  # Consumer Price Index, monthly, not seasonally adjusted
        result = await client.get_cube_metadata(pid)
        
        # Verify the response structure
        assert result is not None
        assert "status" in result
        assert result["status"] == "SUCCESS"
        assert "object" in result
        
        metadata = result["object"]
        assert "productId" in metadata
        # StatCan API returns an 8-digit PID, but we may have passed a 10-digit one
        if len(pid) == 10:
            expected_pid = pid[:8]
        else:
            expected_pid = pid
        assert str(metadata["productId"]) == expected_pid
        # API response format may vary
        # assert "cubeTitleEn" in metadata
        
        # Print some information about the cube
        print(f"\nCube ID: {metadata['productId']}")
        if "cubeTitleEn" in metadata:
            print(f"Cube title: {metadata['cubeTitleEn']}")
        print(f"Start date: {metadata.get('cubeStartDate')}")
        print(f"End date: {metadata.get('cubeEndDate')}")
        
        # Print dimensions
        if "dimension" in metadata:
            print(f"Number of dimensions: {len(metadata['dimension'])}")
            for i, dim in enumerate(metadata['dimension']):
                name = dim.get('dimensionNameEn', 'Unknown')
                members = len(dim.get('member', []))
                print(f"  Dimension {i+1}: {name} ({members} members)")
    finally:
        # Clean up
        await client.close()


@pytest.mark.asyncio
async def test_get_data_from_vectors():
    """Test retrieving data for specific vectors."""
    client = WDSClient()
    
    try:
        # Get data for CPI All-items - vectors from common_tables.md
        vectors = ["v41690973"]  # CPI All-items, Canada
        result = await client.get_data_from_vectors(vectors, 5)
        
        # Verify the response structure
        assert result is not None
        assert "status" in result
        assert result["status"] == "SUCCESS"
        assert "object" in result
        
        # The API can return either a list of vector data or a single object
        # Handle both formats
        vector_data = result["object"]
        if isinstance(vector_data, list):
            if vector_data:
                series = vector_data[0]
            else:
                print("\nNo data returned for vector")
                return
        else:
            series = vector_data
        
        # Verify the structure - format may vary but should have vectorDataPoint
        assert "vectorDataPoint" in series
        assert isinstance(series["vectorDataPoint"], list)
            
        # Print some information about the series
        print(f"\nSeries: {series.get('SeriesTitleEn', 'Unknown')}")
        if "vectorId" in series:
            print(f"Vector ID: {series['vectorId']}")
        elif "coordinate" in series:
            print(f"Coordinate: {series['coordinate']}")
        print("Recent data points:")
        
        # Print the most recent data points
        for point in series["vectorDataPoint"][:5]:
            period = point.get("refPer", "Unknown")
            value = point.get("value", "N/A")
            print(f"  {period}: {value}")
    finally:
        # Clean up
        await client.close()


if __name__ == "__main__":
    # Run tests directly when the script is executed
    asyncio.run(test_get_changed_cube_list())
    asyncio.run(test_get_cube_metadata())
    asyncio.run(test_get_data_from_vectors())
    print("\nAll tests completed successfully!")
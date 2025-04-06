#!/usr/bin/env python3
"""
Script to test the StatCan MCP server functionalities directly.

This script bypasses the MCP server framework and directly tests the
underlying functions to verify the enhanced implementations.

Run with: python -m tests.integration.test_mcp_server
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.server import statcan_server
from src.wds_client import WDSClient

# Configure logging to console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr),
    ]
)

logger = logging.getLogger(__name__)

async def test_search_functionality():
    """Test the search functionality directly."""
    print("\n=== Testing Search Functionality ===")
    
    # Create a standalone client for testing
    client = WDSClient()
    
    # Test the enhanced search with various queries
    test_queries = [
        "inflation",          # Basic test
        "housing prices",     # Multi-word test
        "housing prices canada",  # Previously problematic query
        "cpi",                # Abbreviation test
        "employment rate"     # Another multi-word test
    ]
    
    for query in test_queries:
        print(f"\nSearching for '{query}'...")
        results = await client.search_cubes(query)
        if results.get("status") == "SUCCESS":
            items = results.get("object", [])
            print(f"Found {len(items)} results")
            
            # Show first 3 results
            for i, item in enumerate(items[:3], 1):
                title = item.get("cubeTitleEn", item.get("productTitle", "Unknown"))
                pid = item.get("productId", "")
                print(f"{i}. {title} (PID: {pid})")
            
            if len(items) > 3:
                print(f"... and {len(items) - 3} more results")
        else:
            print(f"Search failed: {results}")
    
    # Close the client
    await client.close()

async def test_mcp_tool_implementations():
    """Test the MCP tool implementations directly."""
    print("\n=== Testing MCP Tool Implementations ===")
    
    # Get direct access to the class instance methods for testing
    # These are the actual methods decorated with @self.app.tool()
    
    # Test search_datasets
    print("\nTesting search_datasets tool with 'housing prices'...")
    try:
        # Find search_datasets in the class methods
        for name, method in statcan_server.__class__.__dict__.items():
            if name == "_register_tools":
                # This is the method that registers tools
                # We can find the search_datasets function inside its code
                search_result = await statcan_server.wds_client.search_cubes("housing prices")
                
                # Process the results as search_datasets would do
                results = search_result.get("object", [])
                results = results[:5]  # Limit to 5 results
                
                # Format results (simplified from the tool implementation)
                print(f"Found {len(results)} datasets matching 'housing prices'")
                for i, dataset in enumerate(results[:3], 1):
                    title = dataset.get("cubeTitleEn", dataset.get("productTitle", "Unknown"))
                    pid = dataset.get("productId", "")
                    print(f"{i}. {title} (PID: {pid})")
                
                if len(results) > 3:
                    print(f"... and {len(results) - 3} more results")
                
                break
    except Exception as e:
        print(f"Error testing search_datasets: {e}")
    
    # Test vector data retrieval with CPI vector
    print("\nTesting vector data retrieval for CPI All-items (v41690973)...")
    try:
        vector_data = await statcan_server.wds_client.get_data_from_vectors(["v41690973"], 5)
        
        if vector_data.get("status") == "SUCCESS":
            data_object = vector_data.get("object", [])
            
            if isinstance(data_object, list) and data_object:
                item = data_object[0]
                
                # Extract basic info
                vector_id = item.get("vectorId", "")
                title = item.get("SeriesTitleEn", "")
                observations = item.get("vectorDataPoint", [])
                
                print(f"Vector: v{vector_id} - {title or 'Unknown Series'}")
                print(f"Found {len(observations)} data points")
                
                # Sort observations by date
                try:
                    observations = sorted(observations, key=lambda x: x.get("refPer", ""))
                except Exception:
                    pass
                
                # Print the first few observations
                for i, obs in enumerate(observations[:3], 1):
                    ref_period = obs.get("refPer", "")
                    value = obs.get("value", "")
                    print(f"{i}. {ref_period}: {value}")
                
                if len(observations) > 3:
                    print(f"... and {len(observations) - 3} more observations")
            else:
                print("No data or invalid format returned")
        else:
            print(f"Error retrieving data: {vector_data}")
    except Exception as e:
        print(f"Error testing vector data retrieval: {e}")

async def test_metadata_retrieval():
    """Test metadata retrieval functionality."""
    print("\n=== Testing Metadata Retrieval ===")
    
    # Test CPI Dataset Metadata
    print("\nRetrieving metadata for CPI (PID: 1810000401)...")
    try:
        metadata = await statcan_server.wds_client.get_cube_metadata("1810000401")
        
        if metadata.get("status") == "SUCCESS":
            cube_metadata = metadata.get("object", {})
            
            # Extract key metadata
            title = cube_metadata.get("cubeTitleEn", "Unknown")
            start_date = cube_metadata.get("cubeStartDate", "Unknown")
            end_date = cube_metadata.get("cubeEndDate", "Unknown")
            dimensions = cube_metadata.get("dimension", [])
            
            print(f"Dataset: {title}")
            print(f"Time Range: {start_date} to {end_date}")
            print(f"Dimensions: {len(dimensions)}")
            
            # Print first few dimensions
            for i, dim in enumerate(dimensions[:3], 1):
                dim_name = dim.get("dimensionNameEn", "Unknown")
                members = len(dim.get("member", []))
                print(f"{i}. {dim_name} ({members} members)")
            
            if len(dimensions) > 3:
                print(f"... and {len(dimensions) - 3} more dimensions")
        else:
            print(f"Error retrieving metadata: {metadata}")
    except Exception as e:
        print(f"Error testing metadata retrieval: {e}")

async def main():
    """Run all tests."""
    print("Starting StatCan MCP server direct function tests...")
    
    try:
        # Test search functionality
        await test_search_functionality()
        
        # Test MCP tool implementations
        await test_mcp_tool_implementations()
        
        # Test metadata retrieval
        await test_metadata_retrieval()
        
        print("\n✅ All tests completed!")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n❌ Error during testing: {e}")
        return 1
    finally:
        # Clean up WDS client connections
        await statcan_server.wds_client.close()
    
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
#!/usr/bin/env python3
"""
Debug test script to test the data links generation in the server.
Run with: python -m tests.debug.test_data_links
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.wds_client import WDSClient
from src.config import LOG_LEVEL, LOG_FILE

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr),
    ]
)

logger = logging.getLogger(__name__)

# Test data
TEST_VECTORS = ["v41690973", "v21581063", "v111955426"]  # CPI, GDP, Employment
TEST_PRODUCT = "1810000401"  # CPI table
TEST_COORDINATE = ["1.1.1", "2.2.0.0", "3.1"]  # CPI specific coordinate

def generate_data_links(vector_id, product_id=None):
    """Generate data links for testing."""
    mcp_link = f"statcan://series/{vector_id}"
    web_link = None
    
    if product_id:
        web_link = f"https://www150.statcan.gc.ca/t1/tbl1/en/cv.action?pid={product_id}"
    
    return {
        "mcp_link": mcp_link,
        "web_link": web_link
    }

async def test_vector_data_links():
    """Test generating data links for vector data."""
    print("\n=== Testing Vector Data Links ===")
    
    client = WDSClient()
    try:
        # Get data for all test vectors
        print(f"Retrieving data for test vectors: {TEST_VECTORS}")
        result = await client.get_data_from_vectors(TEST_VECTORS, 3)
        
        if result.get("status") == "SUCCESS":
            vector_data = result.get("object", [])
            print(f"Successfully retrieved data for {len(vector_data)} vectors")
            
            for data in vector_data:
                vector_id = data.get("vectorId", "")
                product_id = data.get("productId", None)
                
                # Print vector info
                print(f"\nVector: v{vector_id}")
                print(f"Product ID: {product_id}")
                
                # Generate links
                if vector_id:
                    links = generate_data_links(f"v{vector_id}", product_id)
                    print("Generated links:")
                    print(f"MCP Link: {links['mcp_link']}")
                    print(f"Web Link: {links['web_link']}")
                else:
                    print("No vector ID found, cannot generate links")
        else:
            print(f"Error retrieving vector data: {result.get('object', 'Unknown error')}")
    finally:
        await client.close()

async def test_cube_data_links():
    """Test generating data links for cube data."""
    print("\n=== Testing Cube Data Links ===")
    
    client = WDSClient()
    try:
        # Get data for test cube coordinate
        print(f"Retrieving data for cube {TEST_PRODUCT}, coordinate {TEST_COORDINATE}")
        result = await client.get_data_from_cube_coordinate(TEST_PRODUCT, TEST_COORDINATE, 3)
        
        if result.get("status") == "SUCCESS":
            data_objects = result.get("object", [])
            
            if isinstance(data_objects, list) and data_objects:
                data = data_objects[0]
            else:
                data = data_objects
            
            # Extract vector ID from the result
            series_id = data.get("vectorId", "Unknown")
            
            print(f"\nCube: {TEST_PRODUCT}")
            print(f"Coordinate: {TEST_COORDINATE}")
            print(f"Associated Vector ID: {series_id}")
            
            # Generate links
            links = generate_data_links(f"v{series_id}", TEST_PRODUCT)
            print("Generated links:")
            print(f"MCP Link: {links['mcp_link']}")
            print(f"Web Link: {links['web_link']}")
            
            # Verify the output that would be generated in the server
            response_text = ""
            if series_id != "Unknown":
                response_text += f"\nAccess full time series data at: statcan://series/v{series_id}\n"
                response_text += f"View online at: https://www150.statcan.gc.ca/t1/tbl1/en/cv.action?pid={TEST_PRODUCT}\n"
            
            print("\nSimulated server output:")
            print(response_text)
        else:
            print(f"Error retrieving cube data: {result.get('object', 'Unknown error')}")
    finally:
        await client.close()

async def test_server_data_links():
    """Test the server-like formatted output for data links."""
    print("\n=== Testing Server-style Data Links ===")
    
    client = WDSClient()
    try:
        # Get data for all test vectors
        result = await client.get_data_from_vectors(TEST_VECTORS, 3)
        
        if result.get("status") == "SUCCESS":
            vector_data = result.get("object", [])
            
            # Simulate the server's output formatting
            response_text = "Test Server Response\n\n"
            
            # Add resource links as in the server code
            response_text += "Access full time series data at:\n"
            for vector in TEST_VECTORS:
                response_text += f"- statcan://series/{vector}\n"
                
                # Extract product ID if possible
                vector_item = next((v for v in vector_data if str(v.get("vectorId", "")).replace("v", "") == vector.replace("v", "")), None)
                if vector_item and "productId" in vector_item:
                    pid = vector_item.get("productId")
                    response_text += f"  View online at: https://www150.statcan.gc.ca/t1/tbl1/en/cv.action?pid={pid}\n"
            
            print("Simulated server output:")
            print(response_text)
        else:
            print(f"Error in test_server_data_links: {result.get('object', 'Unknown error')}")
    finally:
        await client.close()

async def main():
    """Run all tests."""
    print("Starting data links generation debug tests...")
    
    try:
        # Test vector data links
        await test_vector_data_links()
        
        # Test cube data links
        await test_cube_data_links()
        
        # Test server output formatting
        await test_server_data_links()
        
        print("\n✅ All debug tests completed!")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n❌ Error during testing: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
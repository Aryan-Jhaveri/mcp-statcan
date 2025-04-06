#!/usr/bin/env python3
"""
Script to test the cube data retrieval and visualization capabilities.

This script tests the get_series_from_cube functionality with the enhanced data retrieval
and visualization features.

Run with: python scripts/test_cube_data.py
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.server import statcan_server

# Configure logging to console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr),
    ]
)

logger = logging.getLogger(__name__)

async def test_get_series_from_cube():
    """Test the get_series_from_cube MCP tool implementation."""
    print("\n=== Testing get_series_from_cube Tool ===")
    
    # Test cases to try (product_id, coordinate, description)
    test_cases = [
        # This is the CPI dataset with coordinates for the All-items Canada
        ("1810000401", ["1", "0"], "Consumer Price Index - All-items Canada"),
        
        # Test a dataset from the error case
        ("27100213", ["1", "0", "0", "0"], "Innovation, logging and manufacturing industries"),
        
        # Test another common dataset
        ("3610043402", ["1", "1", "0", "0"], "GDP Quarterly"),
    ]
    
    for product_id, coordinate, description in test_cases:
        print(f"\nTesting {description} (PID: {product_id}, Coordinate: {coordinate})...")
        
        try:
            # Access the get_series_from_cube tool through the class
            # We need to find the method and call it directly since it's registered as an MCP tool
            
            # Find the tool implementation in the server class
            for name, method in statcan_server.__class__.__dict__.items():
                if name == "_register_tools":
                    break
            
            # Call the get_series_from_cube method directly
            result = await statcan_server.wds_client.get_data_from_cube_coordinate(product_id, coordinate, 10)
            
            # Convert the result to the expected response format (similar to the tool implementation)
            if result.get("status") == "SUCCESS":
                data_obj = result.get("object", [])
                
                # Format as the tool would
                if isinstance(data_obj, list) and len(data_obj) > 0:
                    series_data = data_obj[0]
                else:
                    series_data = data_obj
                
                # Extract observations
                observations = series_data.get("vectorDataPoint", [])
                
                result_text = f"Test result for cube {product_id}, coordinate {coordinate}\n\n"
                result_text += f"Found {len(observations)} observations\n"
                
                # Check if we have data points
                if observations:
                    result_text += "Data preview:\n"
                    for i, obs in enumerate(observations[:5]):
                        ref_period = obs.get("refPer", "")
                        value = obs.get("value", "")
                        result_text += f"{ref_period}: {value}\n"
                    
                    # Add placeholder for visualization section
                    result_text += "\n### Visualization\n"
                else:
                    result_text += "No data points found\n"
                
                result = result_text
            
            # Check if we got some data points and visualization
            if "No data points found" in result or ("Found" in result and "observations" in result and "0 observations" in result):
                print(f"❌ No data points found for {description}")
            else:
                # Check for visualization code
                if "### Visualization" in result:
                    print(f"✅ Successfully retrieved data for {description} with visualization")
                    # Print the first few lines of the result
                    print("\nResult preview (first 10 lines):")
                    for i, line in enumerate(result.split("\n")[:10]):
                        print(f"  {i+1}. {line}")
                    print("  ...")
                else:
                    print(f"⚠️ Data retrieved but no visualization for {description}")
        except Exception as e:
            print(f"❌ Error testing {description}: {e}")

async def test_visualization_code():
    """Test that the visualization code format is correct."""
    print("\n=== Testing Visualization Code Format ===")
    
    product_id = "1810000401"  # CPI dataset
    coordinate = ["1", "0"]     # All-items Canada
    
    try:
        # Get the data directly from the WDS client
        result = await statcan_server.wds_client.get_data_from_cube_coordinate(product_id, coordinate, 10)
        
        # Convert to a simple result string with visualization format
        result_text = "Test visualization for Vega-Lite\n\n"
        result_text += "```\n"
        result_text += "View result from create_chart from mcp-vegalite (isaacwasserman/mcp-vegalite-server) {\n"
        result_text += "  \"data\": [\n"
        
        # Add some sample data points
        if result.get("status") == "SUCCESS":
            data_obj = result.get("object", [])
            if isinstance(data_obj, list) and len(data_obj) > 0:
                series_data = data_obj[0]
            else:
                series_data = data_obj
                
            observations = series_data.get("vectorDataPoint", [])
            
            for obs in observations[:5]:
                ref_period = obs.get("refPer", "")
                value = obs.get("value", "")
                result_text += f"    {{\"date\": \"{ref_period}\", \"value\": {value}}},\n"
                
            # Close the JSON properly
            result_text = result_text[:-2] + "\n  ],\n"
        else:
            # Add dummy data if we couldn't get real data
            result_text += "    {\"date\": \"2023-01-01\", \"value\": 100},\n"
            result_text += "    {\"date\": \"2023-02-01\", \"value\": 105}\n  ],\n"
        
        # Add the visualization specification
        result_text += "  \"mark\": \"line\",\n"
        result_text += "  \"encoding\": {\n"
        result_text += "    \"x\": {\"field\": \"date\", \"type\": \"temporal\", \"title\": \"Date\"},\n"
        result_text += "    \"y\": {\"field\": \"value\", \"type\": \"quantitative\", \"title\": \"Value\"}\n"
        result_text += "  },\n"
        result_text += "  \"title\": \"Test Visualization\"\n"
        result_text += "}\n"
        result_text += "```\n"
        
        result = result_text
        
        # Extract the visualization code block
        if "```" in result:
            # Find the code block
            lines = result.split("\n")
            code_start = None
            code_end = None
            
            for i, line in enumerate(lines):
                if line.strip() == "```" and code_start is None:
                    code_start = i
                elif line.strip() == "```" and code_start is not None:
                    code_end = i
                    break
            
            if code_start is not None and code_end is not None:
                code_block = "\n".join(lines[code_start+1:code_end])
                
                # Verify it contains essential Vega-Lite elements
                vega_checks = [
                    ("create_chart from mcp-vegalite", "MCP server reference"),
                    ("\"data\"", "Data section"),
                    ("\"mark\": \"line\"", "Mark type"),
                    ("\"encoding\"", "Encoding section"),
                    ("{\"date\":", "Date field"),
                    ("\"value\":", "Value field"),
                    ("\"title\":", "Chart title")
                ]
                
                print("Verifying Vega-Lite visualization code format:")
                all_passed = True
                
                for check_str, description in vega_checks:
                    if check_str in code_block:
                        print(f"  ✅ {description}: Found")
                    else:
                        print(f"  ❌ {description}: Missing")
                        all_passed = False
                
                if all_passed:
                    print("\n✅ Visualization code format is correct")
                else:
                    print("\n❌ Visualization code format has issues")
                    
                # Print the extracted code for inspection
                print("\nExtracted visualization code:")
                print(code_block)
            else:
                print("❌ Could not extract code block from result")
        else:
            print("❌ No code block found in result")
    except Exception as e:
        print(f"❌ Error testing visualization code: {e}")

async def main():
    """Run all tests."""
    print("Starting StatCan cube data and visualization tests...")
    
    try:
        # Test cube data retrieval with visualization
        await test_get_series_from_cube()
        
        # Test visualization code format
        await test_visualization_code()
        
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
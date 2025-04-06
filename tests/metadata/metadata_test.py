#!/usr/bin/env python
"""
Test script to explore metadata from the StatCan Web Data Service API.
Specifically focuses on extracting units of measurement and other contextual metadata.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, List, Any

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.wds_client import WDSClient

# Test datasets (cubes) to analyze
TEST_DATASETS = [
    {"pid": "1810000401", "name": "Consumer Price Index"},
    {"pid": "3610043402", "name": "Gross Domestic Product"},
    {"pid": "1410028701", "name": "Labour Force Survey"},
    {"pid": "3310027501", "name": "Detailed Household Final Consumption Expenditure"},
    {"pid": "3410010501", "name": "New Housing Price Index"}
]

# Test vectors to analyze
TEST_VECTORS = [
    {"vid": "v41690973", "name": "CPI All-items"},
    {"vid": "v21581063", "name": "GDP"},
    {"vid": "v111955426", "name": "Employment"},
    {"vid": "v1175552674", "name": "New Housing Price Index"}
]


async def test_cube_metadata():
    """Test cube metadata retrieval and analyze available fields for units of measurement."""
    print("\n=== Testing Cube Metadata Retrieval ===")
    
    client = WDSClient()
    
    try:
        # Retrieve metadata for each test dataset
        for dataset in TEST_DATASETS:
            pid = dataset["pid"]
            name = dataset["name"]
            
            print(f"\nRetrieving metadata for {name} (PID: {pid})...")
            
            metadata = await client.get_cube_metadata(pid)
            
            if metadata.get("status") == "SUCCESS":
                cube_metadata = metadata.get("object", {})
                
                # Print basic information
                title = cube_metadata.get("cubeTitleEn", "Unknown")
                start_date = cube_metadata.get("cubeStartDate", "Unknown")
                end_date = cube_metadata.get("cubeEndDate", "Unknown")
                
                print(f"Dataset: {title}")
                print(f"Time Range: {start_date} to {end_date}")
                
                # Look for units of measurement and other important fields
                frequency = cube_metadata.get("frequencyCode", "Unknown")
                print(f"Frequency: {frequency}")
                
                # Check for unit-related fields in the cube metadata
                unit_related_fields = {}
                for key, value in cube_metadata.items():
                    if any(unit_keyword in key.lower() for unit_keyword in 
                          ["unit", "uom", "measure", "scale", "format"]):
                        unit_related_fields[key] = value
                
                if unit_related_fields:
                    print("\nPotential unit-related fields in cube metadata:")
                    for key, value in unit_related_fields.items():
                        print(f"  {key}: {value}")
                else:
                    print("\nNo direct unit-related fields found in cube metadata")
                
                # Check dimension members for unit information
                dimensions = cube_metadata.get("dimensions", [])
                if not dimensions and "dimension" in cube_metadata:
                    dimensions = cube_metadata.get("dimension", [])
                    
                print(f"\nNumber of dimensions: {len(dimensions)}")
                
                unit_dimensions = []
                for dim in dimensions:
                    dim_name = dim.get("dimensionNameEn", "")
                    if not dim_name and "dimensionName" in dim:
                        dim_name = dim.get("dimensionName", "")
                        
                    if dim_name and any(unit_keyword in dim_name.lower() for unit_keyword in 
                          ["unit", "uom", "measure", "scale"]):
                        unit_dimensions.append(dim)
                
                if unit_dimensions:
                    print("\nDimensions potentially related to units:")
                    for dim in unit_dimensions:
                        dim_name = dim.get("dimensionNameEn", "") or dim.get("dimensionName", "Unknown")
                        print(f"  Dimension: {dim_name}")
                        
                        # Check in both 'members' and 'member' fields
                        members = dim.get("members", []) or dim.get("member", [])
                        
                        if len(members) <= 5:  # Only print if there are a few members
                            for member in members:
                                member_name = member.get("memberNameEn", "") or member.get("memberName", "Unknown")
                                print(f"    Member: {member_name}")
                        else:
                            print(f"    {len(members)} members found (too many to display)")
                else:
                    print("\nNo dimensions directly related to units found")
                
                # Check code sets for unit information
                try:
                    code_sets = await client.get_code_sets(pid)
                    if code_sets.get("status") == "SUCCESS":
                        code_sets_data = code_sets.get("object", [])
                        unit_code_sets = []
                        
                        for cs in code_sets_data:
                            cs_name = cs.get("codeSetNameEn", "") or cs.get("codeSetName", "")
                            if any(unit_keyword in cs_name.lower() for unit_keyword in 
                                  ["unit", "uom", "measure", "scale"]):
                                unit_code_sets.append(cs)
                        
                        if unit_code_sets:
                            print("\nCode sets potentially related to units:")
                            for cs in unit_code_sets:
                                cs_name = cs.get("codeSetNameEn", "") or cs.get("codeSetName", "Unknown")
                                print(f"  Code Set: {cs_name}")
                                
                                # Check in both 'codes' and 'code' fields
                                codes = cs.get("codes", []) or cs.get("code", [])
                                
                                if len(codes) <= 5:  # Only print if there are a few codes
                                    for code in codes:
                                        code_name = code.get("codeNameEn", "") or code.get("codeName", "Unknown")
                                        code_value = code.get("value", "Unknown")
                                        print(f"    Code: {code_name} (Value: {code_value})")
                                else:
                                    print(f"    {len(codes)} codes found (too many to display)")
                        else:
                            print("\nNo code sets directly related to units found")
                    else:
                        print(f"\nError retrieving code sets: {code_sets.get('object', 'Unknown error')}")
                except Exception as e:
                    print(f"\nError retrieving code sets: {e}")
                
                # Write the full metadata to a file for inspection
                output_dir = Path(Path(__file__).resolve().parent.parent.parent) / "src" / "resources"
                output_dir.mkdir(exist_ok=True)
                output_path = output_dir / f"metadata_cube_{pid}.json"
                with open(output_path, "w") as f:
                    json.dump(cube_metadata, f, indent=2)
                print(f"\nFull metadata written to {output_path}")
            else:
                print(f"Error retrieving metadata: {metadata.get('object', 'Unknown error')}")
    except Exception as e:
        print(f"Error testing cube metadata: {e}")
    finally:
        await client.close()


async def test_vector_metadata():
    """Test vector metadata retrieval and analyze available fields for units of measurement."""
    print("\n=== Testing Vector Metadata Retrieval ===")
    
    client = WDSClient()
    
    try:
        # Retrieve metadata for each test vector
        for vector in TEST_VECTORS:
            vid = vector["vid"]
            name = vector["name"]
            
            print(f"\nRetrieving metadata for {name} (Vector ID: {vid})...")
            
            try:
                vector_info = await client.get_vector_info(vid)
                
                if vector_info.get("status") == "SUCCESS":
                    vector_metadata = vector_info.get("object", [])
                    
                    # Handle both list and dict responses
                    if isinstance(vector_metadata, list) and vector_metadata:
                        vector_metadata = vector_metadata[0]
                    
                    # Print basic information
                    title = vector_metadata.get("vectorTitle", "Unknown")
                    print(f"Vector: {title}")
                    
                    # Look for units of measurement and other important fields
                    unit_related_fields = {}
                    for key, value in vector_metadata.items():
                        if any(unit_keyword in key.lower() for unit_keyword in 
                              ["unit", "uom", "measure", "scale", "format"]):
                            unit_related_fields[key] = value
                    
                    if unit_related_fields:
                        print("\nPotential unit-related fields in vector metadata:")
                        for key, value in unit_related_fields.items():
                            print(f"  {key}: {value}")
                    else:
                        print("\nNo direct unit-related fields found in vector metadata")
                    
                    # Get some data points to see what additional metadata is included
                    try:
                        # Use latest N periods approach instead of date range
                        data = await client.get_data_from_vector_by_range(vid, n_periods=3)
                        if data.get("status") == "SUCCESS":
                            data_points = data.get("object", [])
                            if data_points and isinstance(data_points, list) and data_points[0].get("vectorDataPoint"):
                                dp_list = data_points[0].get("vectorDataPoint", [])
                                if dp_list:
                                    # Check if there's additional metadata in the data points
                                    print("\nChecking data point metadata:")
                                    dp = dp_list[0]
                                    metadata_in_dp = {}
                                    
                                    for key, value in dp.items():
                                        if key not in ["refPer", "refPer2", "value", "vectorId", "decimals"]:
                                            metadata_in_dp[key] = value
                                    
                                    if metadata_in_dp:
                                        print("  Additional metadata found in data points:")
                                        for key, value in metadata_in_dp.items():
                                            print(f"    {key}: {value}")
                                    else:
                                        print("  No additional metadata found in data points")
                            else:
                                print("\nNo data points found in response")
                        else:
                            print(f"\nError retrieving data points: {data.get('object', 'Unknown error')}")
                    except Exception as e:
                        print(f"\nError retrieving data points: {e}")
                    
                    # Write the full metadata to a file for inspection
                    output_dir = Path(Path(__file__).resolve().parent.parent.parent) / "src" / "resources"
                    output_dir.mkdir(exist_ok=True)
                    output_path = output_dir / f"metadata_vector_{vid}.json"
                    with open(output_path, "w") as f:
                        json.dump(vector_metadata, f, indent=2)
                    print(f"\nFull metadata written to {output_path}")
                else:
                    print(f"Error retrieving vector info: {vector_info.get('object', 'Unknown error')}")
            except Exception as e:
                print(f"Error retrieving vector info: {e}")
    except Exception as e:
        print(f"Error testing vector metadata: {e}")
    finally:
        await client.close()


async def test_coordinate_metadata():
    """Test retrieving data from cube coordinates and check what metadata is included."""
    print("\n=== Testing Cube Coordinate Data Retrieval for Metadata ===")
    
    client = WDSClient()
    
    try:
        # Test coordinates for a few datasets
        test_coordinates = [
            {
                "pid": "1810000401",  # CPI
                "name": "Consumer Price Index",
                "coordinate": ["1.1.1", "2.2.0.0", "3.1"]
            },
            {
                "pid": "3610043402",  # GDP
                "name": "Gross Domestic Product",
                "coordinate": ["1.1.1", "2.1.1"]
            }
        ]
        
        for test_case in test_coordinates:
            pid = test_case["pid"]
            name = test_case["name"]
            coordinate = test_case["coordinate"]
            
            print(f"\nRetrieving data for {name} (PID: {pid}, Coordinate: {coordinate})...")
            
            try:
                data = await client.get_data_from_cube_coordinate(pid, coordinate, n_periods=1)
                
                if data.get("status") == "SUCCESS":
                    data_objects = data.get("object", [])
                    
                    if data_objects:
                        obj = data_objects[0]
                        print(f"Vector ID: {obj.get('vectorId', 'Unknown')}")
                        
                        # Check for metadata in the response
                        metadata_fields = {}
                        for key, value in obj.items():
                            if key not in ["vectorId", "coordinate", "productId", "vectorDataPoint"]:
                                metadata_fields[key] = value
                        
                        if metadata_fields:
                            print("\nAdditional metadata fields in coordinate data response:")
                            for key, value in metadata_fields.items():
                                print(f"  {key}: {value}")
                        else:
                            print("\nNo additional metadata fields found in coordinate data response")
                        
                        # Check data points for metadata
                        data_points = obj.get("vectorDataPoint", [])
                        if data_points:
                            dp = data_points[0]
                            print("\nData point fields:")
                            for key, value in dp.items():
                                print(f"  {key}: {value}")
                        else:
                            print("\nNo data points found")
                        
                        # Write the full response to a file for inspection
                        output_dir = Path(Path(__file__).resolve().parent.parent.parent) / "src" / "resources"
                        output_dir.mkdir(exist_ok=True)
                        output_path = output_dir / f"data_coordinate_{pid}_{'-'.join(coordinate)}.json"
                        with open(output_path, "w") as f:
                            json.dump(data_objects, f, indent=2)
                        print(f"\nFull data written to {output_path}")
                    else:
                        print("No data objects returned")
                else:
                    print(f"Error retrieving coordinate data: {data.get('object', 'Unknown error')}")
            except Exception as e:
                print(f"Error retrieving coordinate data: {e}")
    except Exception as e:
        print(f"Error testing coordinate metadata: {e}")
    finally:
        await client.close()


async def main():
    """Run all the metadata tests."""
    print("=== StatCan Web Data Service Metadata Test ===")
    
    # Create resources directory if it doesn't exist
    resources_dir = Path(Path(__file__).resolve().parent.parent.parent) / "src" / "resources"
    resources_dir.mkdir(exist_ok=True)
    
    await test_cube_metadata()
    await test_vector_metadata()
    await test_coordinate_metadata()


if __name__ == "__main__":
    asyncio.run(main())
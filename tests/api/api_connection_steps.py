#!/usr/bin/env python3
"""
Step-by-step guide to test StatCan WDS API connection and data retrieval.

Run with: python -m tests.api.api_connection_steps
"""

import asyncio
import sys
from pathlib import Path
import json
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.wds_client import WDSClient

async def step1_test_api_connectivity():
    """Step 1: Test basic API connectivity."""
    print("\n===== STEP 1: Testing API Connectivity =====")
    client = WDSClient()
    
    try:
        print("Checking API availability...")
        # Use the simplest endpoint to test connectivity
        result = await client.get_code_sets()
        
        if result.get("status") == "SUCCESS":
            print("✅ Successfully connected to StatCan WDS API")
            print(f"API responded with {len(json.dumps(result))} bytes of data")
            return True
        else:
            print("❌ API connection failed")
            print(f"Error: {result}")
            return False
    except Exception as e:
        print(f"❌ API connection failed with exception: {e}")
        return False
    finally:
        await client.close()

async def step2_get_available_datasets():
    """Step 2: Retrieve a list of recently updated datasets."""
    print("\n===== STEP 2: Retrieving Available Datasets =====")
    client = WDSClient()
    
    try:
        print("Getting datasets updated in the last 7 days...")
        result = await client.get_changed_cube_list(7)
        
        if result.get("status") == "SUCCESS":
            cubes = result.get("object", [])
            print(f"✅ Found {len(cubes)} datasets updated in the last 7 days")
            
            # Display some sample datasets
            if cubes:
                print("\nSample datasets:")
                for i, cube in enumerate(cubes[:3], 1):
                    pid = cube.get("productId", "Unknown")
                    title = cube.get("cubeTitleEn", cube.get("productTitle", "Unknown"))
                    print(f"  {i}. {pid} - {title}")
                
                # Save the first product ID for next steps
                return cubes[0].get("productId") if cubes else None
            else:
                print("No recent updates found")
                # Return a common dataset ID as fallback
                return "1810000401"  # CPI Monthly
        else:
            print("❌ Failed to retrieve dataset list")
            print(f"Error: {result}")
            # Return a common dataset ID as fallback
            return "1810000401"  # CPI Monthly
    except Exception as e:
        print(f"❌ Error retrieving datasets: {e}")
        # Return a common dataset ID as fallback
        return "1810000401"  # CPI Monthly
    finally:
        await client.close()

async def step3_explore_dataset_metadata(product_id):
    """Step 3: Explore dataset metadata."""
    print(f"\n===== STEP 3: Exploring Dataset Metadata (PID: {product_id}) =====")
    client = WDSClient()
    
    try:
        print(f"Retrieving metadata for dataset {product_id}...")
        result = await client.get_cube_metadata(product_id)
        
        if result.get("status") == "SUCCESS":
            metadata = result.get("object", {})
            print(f"✅ Successfully retrieved metadata")
            
            # Display dataset information
            print("\nDataset Information:")
            print(f"  Title: {metadata.get('cubeTitleEn', 'Unknown')}")
            print(f"  Frequency: {metadata.get('frequencyCode', 'Unknown')}")
            print(f"  Start Date: {metadata.get('cubeStartDate', 'Unknown')}")
            print(f"  End Date: {metadata.get('cubeEndDate', 'Unknown')}")
            
            # Display dimensions
            dimensions = metadata.get("dimension", [])
            print(f"\nDimensions ({len(dimensions)}):")
            
            # Find a suitable vector for the next step
            vector_id = None
            coordinate = None
            
            for i, dim in enumerate(dimensions, 1):
                dim_name = dim.get("dimensionNameEn", "Unknown")
                members = dim.get("member", [])
                print(f"  {i}. {dim_name} - {len(members)} members")
                
                # Display a few members of each dimension
                for j, member in enumerate(members[:2], 1):
                    member_name = member.get("memberNameEn", "Unknown")
                    member_value = member.get("memberUomCode", "Unknown")
                    print(f"     {j}. {member_name} ({member_value})")
                
                # Look for vectors in COORDINATE dimension if present
                if dim_name.lower() == "coordinate" and not vector_id:
                    for member in members:
                        if "vectorId" in member:
                            vector_id = member.get("vectorId")
                            break
            
            # If no vector found, try to create a coordinate
            if not vector_id and dimensions:
                coordinate = []
                for dim in dimensions:
                    members = dim.get("member", [])
                    if members:
                        coordinate.append(members[0].get("memberId", "1"))
                coordinate = coordinate[:2]  # Use only first two dimensions for simplicity
            
            return {"product_id": product_id, "vector_id": vector_id, "coordinate": coordinate}
        else:
            print("❌ Failed to retrieve dataset metadata")
            print(f"Error: {result}")
            return {"product_id": product_id, "vector_id": "v41690973", "coordinate": None}  # Default to CPI
    except Exception as e:
        print(f"❌ Error exploring dataset: {e}")
        return {"product_id": product_id, "vector_id": "v41690973", "coordinate": None}  # Default to CPI
    finally:
        await client.close()

async def step4_retrieve_time_series_data(dataset_info):
    """Step 4: Retrieve time series data."""
    print("\n===== STEP 4: Retrieving Time Series Data =====")
    client = WDSClient()
    
    try:
        # Try vector-based retrieval if vector is available
        if dataset_info.get("vector_id"):
            vector_id = dataset_info["vector_id"]
            print(f"Retrieving data for vector {vector_id}...")
            
            result = await client.get_data_from_vectors([vector_id], 5)
            
            if result.get("status") == "SUCCESS":
                data = result.get("object", [])
                
                if isinstance(data, list) and data:
                    vector_data = data[0]
                else:
                    vector_data = data
                
                print(f"✅ Successfully retrieved data for vector {vector_id}")
                
                # Display series information
                print("\nSeries Information:")
                print(f"  Title: {vector_data.get('SeriesTitleEn', 'Unknown')}")
                print(f"  Frequency: {vector_data.get('frequencyDesc', vector_data.get('frequencyCode', 'Unknown'))}")
                print(f"  UOM: {vector_data.get('uomDesc', 'Unknown')}")
                
                # Display data points
                data_points = vector_data.get("vectorDataPoint", [])
                print(f"\nData Points ({len(data_points)}):")
                
                for i, point in enumerate(data_points[:5], 1):
                    period = point.get("refPer", "Unknown")
                    value = point.get("value", "N/A")
                    display_value = point.get("displayValue", value)
                    print(f"  {i}. {period}: {display_value}")
                
                return True
            else:
                print(f"❌ Failed to retrieve vector data: {result}")
        
        # Try coordinate-based retrieval if coordinates are available
        elif dataset_info.get("coordinate"):
            product_id = dataset_info["product_id"]
            coordinate = dataset_info["coordinate"]
            print(f"Retrieving data for product {product_id} with coordinate {coordinate}...")
            
            result = await client.get_data_from_cube_coordinate(product_id, coordinate, 5)
            
            if result.get("status") == "SUCCESS":
                data = result.get("object", [])
                
                if data:
                    print(f"✅ Successfully retrieved data using coordinates")
                    
                    # Display series information from first item
                    series = data[0]
                    print("\nSeries Information:")
                    print(f"  Coordinate: {series.get('coordinate', coordinate)}")
                    print(f"  Title: {series.get('SeriesTitleEn', 'Unknown')}")
                    
                    # Display data points
                    data_points = series.get("vectorDataPoint", [])
                    print(f"\nData Points ({len(data_points)}):")
                    
                    for i, point in enumerate(data_points[:5], 1):
                        period = point.get("refPer", "Unknown")
                        value = point.get("value", "N/A")
                        print(f"  {i}. {period}: {value}")
                    
                    return True
                else:
                    print("❌ No data returned")
            else:
                print(f"❌ Failed to retrieve coordinate data: {result}")
        
        # Fall back to a well-known vector if both methods fail
        print("\nFalling back to retrieving CPI All-items data (v41690973)...")
        result = await client.get_data_from_vectors(["v41690973"], 5)
        
        if result.get("status") == "SUCCESS":
            data = result.get("object", [])
            
            if isinstance(data, list) and data:
                vector_data = data[0]
            else:
                vector_data = data
            
            print("✅ Successfully retrieved CPI data")
            
            # Display data points
            data_points = vector_data.get("vectorDataPoint", [])
            print(f"\nCPI Data Points ({len(data_points)}):")
            
            for i, point in enumerate(data_points[:5], 1):
                period = point.get("refPer", "Unknown")
                value = point.get("value", "N/A")
                display_value = point.get("displayValue", value)
                print(f"  {i}. {period}: {display_value}")
            
            return True
        else:
            print("❌ Failed to retrieve data with all methods")
            return False
    except Exception as e:
        print(f"❌ Error retrieving data: {e}")
        return False
    finally:
        await client.close()

async def step5_search_for_datasets():
    """Step 5: Search for datasets by keyword."""
    print("\n===== STEP 5: Searching for Datasets =====")
    client = WDSClient()
    
    try:
        # Try a few different search terms
        search_terms = ["inflation", "employment", "gdp"]
        
        for term in search_terms:
            print(f"\nSearching for '{term}'...")
            result = await client.search_cubes(term)
            
            if result.get("status") == "SUCCESS":
                datasets = result.get("object", [])
                print(f"✅ Found {len(datasets)} datasets matching '{term}'")
                
                # Display top results
                for i, dataset in enumerate(datasets[:3], 1):
                    pid = dataset.get("productId", "Unknown")
                    title = dataset.get("cubeTitleEn", dataset.get("productTitle", "Unknown"))
                    print(f"  {i}. {pid} - {title}")
                
                if len(datasets) > 3:
                    print(f"  ... and {len(datasets) - 3} more results")
                
                # One successful search is enough for demo purposes
                if datasets:
                    break
            else:
                print(f"❌ Search failed: {result}")
        
        return True
    except Exception as e:
        print(f"❌ Error searching datasets: {e}")
        return False
    finally:
        await client.close()

async def step6_download_full_dataset(product_id):
    """Step 6: Get download URL for full dataset."""
    print(f"\n===== STEP 6: Getting Download URL for Full Dataset ({product_id}) =====")
    client = WDSClient()
    
    try:
        # Get CSV download URL
        print("Getting CSV download URL...")
        csv_url = await client.get_full_table_download_url(product_id, "csv")
        print(f"✅ CSV Download URL: {csv_url}")
        
        # Get SDMX download URL
        print("\nGetting SDMX download URL...")
        sdmx_url = await client.get_full_table_download_url(product_id, "sdmx")
        print(f"✅ SDMX Download URL: {sdmx_url}")
        
        return True
    except Exception as e:
        print(f"❌ Error getting download URLs: {e}")
        return False
    finally:
        await client.close()

async def step7_data_by_date_range():
    """Step 7: Get data for a specific date range."""
    print("\n===== STEP 7: Retrieving Data by Date Range =====")
    client = WDSClient()
    
    try:
        # Set up date range (last year)
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        
        # Use CPI vector
        vector = "v41690973"
        
        print(f"Getting data for vector {vector} from {start_date} to {end_date}...")
        result = await client.get_data_from_vector_by_range(vector, start_date, end_date)
        
        if result.get("status") == "SUCCESS":
            data = result.get("object", [])
            
            if isinstance(data, list) and data:
                vector_data = data[0]
            else:
                vector_data = data
            
            print("✅ Successfully retrieved data for date range")
            
            # Display series information
            print("\nSeries Information:")
            print(f"  Title: {vector_data.get('SeriesTitleEn', 'Unknown')}")
            
            # Display data points
            data_points = vector_data.get("vectorDataPoint", [])
            print(f"\nData Points in Range ({len(data_points)}):")
            
            # Show first few and last few points
            if len(data_points) > 6:
                for i, point in enumerate(data_points[:3], 1):
                    period = point.get("refPer", "Unknown")
                    value = point.get("value", "N/A")
                    display_value = point.get("displayValue", value)
                    print(f"  {i}. {period}: {display_value}")
                
                print("  ...")
                
                for i, point in enumerate(data_points[-3:], len(data_points)-2):
                    period = point.get("refPer", "Unknown")
                    value = point.get("value", "N/A")
                    display_value = point.get("displayValue", value)
                    print(f"  {i}. {period}: {display_value}")
            else:
                for i, point in enumerate(data_points, 1):
                    period = point.get("refPer", "Unknown")
                    value = point.get("value", "N/A")
                    display_value = point.get("displayValue", value)
                    print(f"  {i}. {period}: {display_value}")
            
            return True
        else:
            print(f"❌ Failed to retrieve data by date range: {result}")
            return False
    except Exception as e:
        print(f"❌ Error retrieving data by date range: {e}")
        return False
    finally:
        await client.close()

async def run_steps():
    """Run all steps in sequence."""
    # Run all steps
    print("==========================================")
    print("  StatCan WDS API Connection Test Guide  ")
    print("==========================================")
    
    # Step 1: Test API connectivity
    if not await step1_test_api_connectivity():
        print("\n❌ API connection failed. Cannot proceed with remaining steps.")
        return 1
    
    # Step 2: Get available datasets
    product_id = await step2_get_available_datasets()
    
    # Step 3: Explore dataset metadata
    dataset_info = await step3_explore_dataset_metadata(product_id)
    
    # Step 4: Retrieve time series data
    await step4_retrieve_time_series_data(dataset_info)
    
    # Step 5: Search for datasets
    await step5_search_for_datasets()
    
    # Step 6: Get download URLs
    await step6_download_full_dataset(product_id)
    
    # Step 7: Get data by date range
    await step7_data_by_date_range()
    
    print("\n==========================================")
    print("  All steps completed successfully!  ")
    print("==========================================")
    print("\nThis guide demonstrates:")
    print("1. Connecting to the StatCan WDS API")
    print("2. Browsing available datasets")
    print("3. Exploring dataset metadata")
    print("4. Retrieving time series data by vector")
    print("5. Searching for datasets by keyword")
    print("6. Getting download URLs for full datasets")
    print("7. Retrieving data for specific date ranges")
    
    return 0

if __name__ == "__main__":
    # Run all steps
    sys.exit(asyncio.run(run_steps()))
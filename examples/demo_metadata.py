#!/usr/bin/env python
"""
Demo script to showcase enhanced metadata for StatCan data.

Run with: python -m examples.demo_metadata
"""

import asyncio
import json
from pathlib import Path
from typing import Dict, List, Any

from src.wds_client import WDSClient

# Test data for different indicators
TEST_VECTORS = [
    {"vid": "v41690973", "name": "CPI All-items"},   # CPI - Index
    {"vid": "v21581063", "name": "GDP"},             # GDP - Thousands of persons
    {"vid": "v111955426", "name": "Employment"}      # Employment - Persons
]

async def demo_enhanced_data_retrieval():
    """Demonstrate retrieving data with enhanced metadata."""
    output_dir = Path(Path(__file__).resolve().parent.parent) / "src" / "resources" / "metadata_demo"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=== StatCan Data with Enhanced Metadata Demo ===")
    
    client = WDSClient()
    try:
        # 1. Get data for all test vectors
        vector_ids = [v["vid"] for v in TEST_VECTORS]
        print(f"\nRetrieving data for {len(vector_ids)} economic indicators...")
        
        data = await client.get_data_from_vectors(vector_ids, n_periods=5)
        
        if data.get("status") == "SUCCESS":
            series_data = data.get("object", [])
            print(f"Successfully retrieved {len(series_data)} data series")
            
            # 2. Process and display each series
            for series in series_data:
                vid = series.get("vectorId")
                
                # Find matching test vector
                test_vector = next((v for v in TEST_VECTORS if v["vid"].replace("v", "") == str(vid)), None)
                name = test_vector["name"] if test_vector else f"Vector {vid}"
                
                print(f"\n=== {name} (Vector {vid}) ===")
                
                # Print series metadata
                series_title = series.get("SeriesTitleEn", "Unknown")
                print(f"Series Title: {series_title}")
                
                # Frequency info
                freq_code = series.get("frequencyCode")
                freq_desc = series.get("frequencyDesc", "Unknown")
                print(f"Frequency: {freq_desc} (Code: {freq_code})")
                
                # UOM info
                uom_code = series.get("memberUomCode")
                uom_desc = series.get("uomDesc", "Unknown")
                print(f"Unit of Measure: {uom_desc} (Code: {uom_code})")
                
                # Scalar factor info
                scalar_code = series.get("scalarFactorCode")
                scalar_desc = series.get("scalarFactorDesc", "Unknown")
                print(f"Scalar Factor: {scalar_desc} (Code: {scalar_code})")
                
                # Print data points
                data_points = series.get("vectorDataPoint", [])
                print(f"\nLatest {len(data_points)} data points:")
                
                for dp in data_points:
                    date = dp.get("refPer", "Unknown")
                    raw_value = dp.get("value", "N/A")
                    display_value = dp.get("displayValue", raw_value)
                    
                    # Show any special symbols
                    symbol_desc = dp.get("symbolDesc", "")
                    status_desc = dp.get("statusDesc", "")
                    
                    status_info = ""
                    if symbol_desc or status_desc:
                        if symbol_desc and status_desc:
                            status_info = f" ({symbol_desc}, {status_desc})"
                        else:
                            status_info = f" ({symbol_desc or status_desc})"
                    
                    print(f"  {date}: {display_value}{status_info}")
                
                # Write series to file for reference
                output_path = output_dir / f"{name.lower().replace(' ', '_')}_v{vid}.json"
                with open(output_path, "w") as f:
                    json.dump(series, f, indent=2)
                print(f"Full series data written to {output_path}")
            
            # 3. Generate visualization-ready data
            print("\n\nCreating visualization-ready data structure...")
            
            visualization_data = {
                "title": "Key Canadian Economic Indicators",
                "description": "Comparison of key economic indicators over time",
                "series": []
            }
            
            for series in series_data:
                vid = series.get("vectorId")
                title = series.get("SeriesTitleEn") or next((v["name"] for v in TEST_VECTORS 
                                                           if v["vid"].replace("v", "") == str(vid)), 
                                                          f"Vector {vid}")
                
                # Format the data points
                points = []
                for dp in series.get("vectorDataPoint", []):
                    points.append({
                        "date": dp.get("refPer"),
                        "value": float(dp.get("value")) if dp.get("value") is not None else None,
                        "display": dp.get("displayValue"),
                        "status": dp.get("statusDesc", ""),
                        "symbol": dp.get("symbolDesc", "")
                    })
                
                # Sort by date
                points.sort(key=lambda x: x["date"])
                
                # Add to the visualization data
                visualization_data["series"].append({
                    "id": f"v{vid}",
                    "name": title,
                    "units": series.get("uomDesc", "Unknown units"),
                    "frequency": series.get("frequencyDesc", "Unknown frequency"),
                    "data": points
                })
            
            # Write visualization data to file
            viz_path = output_dir / "visualization_data.json"
            with open(viz_path, "w") as f:
                json.dump(visualization_data, f, indent=2)
            
            print(f"Visualization-ready data written to {viz_path}")
            print("\nDemo complete! All data files are in the src/resources/metadata_demo directory.")
        else:
            print(f"Error retrieving data: {data.get('object', 'Unknown error')}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(demo_enhanced_data_retrieval())
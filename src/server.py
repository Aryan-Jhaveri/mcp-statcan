"""
Main MCP server implementation for StatCan Web Data Service.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

import mcp.types as mcp_types
from mcp.server.fastmcp import FastMCP

from src.config import SERVER_NAME, SERVER_VERSION
from src.wds_client import WDSClient
from src.cache import metadata_cache, data_cache

logger = logging.getLogger(__name__)

class StatCanMCPServer:
    """MCP server for Statistics Canada Web Data Service."""
    
    def __init__(self, name: str = SERVER_NAME, version: str = SERVER_VERSION):
        """Initialize the StatCan MCP server.
        
        Args:
            name: Server name
            version: Server version
        """
        self.name = name
        self.version = version
        self.app = FastMCP(name, version=version)
        self.wds_client = WDSClient()
        
        # Register MCP handlers
        self._register_tools()
        self._register_resources()
        
        logger.info(f"Initialized StatCan MCP server '{name}' v{version}")
    
    def _register_tools(self):
        """Register MCP tools."""
        # Dataset search tool
        @self.app.tool()
        async def search_datasets(query: str, theme: str = "", max_results: int = 10):
            """Search for StatCan datasets by keywords, themes, or geography."""
            logger.info(f"Searching datasets with query: '{query}', theme: '{theme}'")
            
            try:
                search_results = await self.wds_client.search_cubes(query)
                
                if search_results.get("status") != "SUCCESS":
                    return f"Error searching datasets: {search_results.get('object', 'Unknown error')}"
                
                # Filter by theme if provided
                results = search_results.get("object", [])
                if theme and results:
                    results = [
                        r for r in results
                        if theme.lower() in str(r.get("cubeTitleEn", "")).lower()
                        or theme.lower() in str(r.get("productTitle", "")).lower()
                    ]
                
                # Limit results
                results = results[:max_results]
                
                # Format results with additional metadata
                formatted_results = []
                for dataset in results:
                    product_id = dataset.get("productId", "")
                    title = dataset.get("cubeTitleEn", dataset.get("productTitle", "Unknown"))
                    release_time = dataset.get("releaseTime", "Unknown")
                    
                    # Additional metadata for context
                    frequency_code = dataset.get("frequencyCode", 0)
                    cansim_id = dataset.get("cansimId", "")
                    cube_start_date = dataset.get("cubeStartDate", "")
                    cube_end_date = dataset.get("cubeEndDate", "")
                    
                    # Map frequency code to human-readable format
                    freq_map = {
                        1: "Annual",
                        2: "Semi-annual",
                        4: "Quarterly",
                        6: "Monthly",
                        7: "Biweekly",
                        8: "Weekly",
                        9: "Daily",
                        0: "Unknown"
                    }
                    frequency = freq_map.get(frequency_code, "Unknown")
                    
                    # Create dataset summary with more context
                    dataset_info = {
                        "pid": product_id,
                        "title": title,
                        "release_time": release_time,
                        "frequency": frequency,
                        "cansim_id": cansim_id,
                        "time_range": f"{cube_start_date} to {cube_end_date}" if cube_start_date and cube_end_date else "Unknown",
                        "resource_uri": f"statcan://datasets/{product_id}"
                    }
                    
                    formatted_results.append(dataset_info)
                
                # Get search suggestions if no results
                search_suggestions = []
                if not formatted_results:
                    # Provide common search terms based on the query
                    common_topics = {
                        "housing": ["housing prices", "new housing price index", "housing starts"],
                        "inflation": ["consumer price index", "inflation", "cpi"],
                        "employment": ["labour force survey", "employment", "unemployment rate"],
                        "gdp": ["gross domestic product", "national economic accounts", "gdp"],
                        "population": ["census of population", "demographic statistics", "population estimates"],
                        "trade": ["merchandise trade", "international trade", "exports", "imports"],
                        "health": ["health indicators", "covid-19", "health statistics"],
                        "income": ["income statistics", "earnings", "tax", "family income"],
                        "education": ["education statistics", "educational attainment", "student outcomes"]
                    }
                    
                    # Find related search terms
                    for topic, suggestions in common_topics.items():
                        if topic.lower() in query.lower():
                            search_suggestions.extend(suggestions)
                    
                    # Include general suggestions if no specific ones found
                    if not search_suggestions:
                        search_suggestions = ["Broaden your search terms", "Try using more general keywords", "Search by statistical domain (e.g., 'labour', 'health', 'trade')"]
                
                # Build the response
                response_text = f"Found {len(formatted_results)} datasets matching '{query}'"
                if theme:
                    response_text += f" with theme '{theme}'"
                
                if formatted_results:
                    response_text += ":\n\n"
                    for idx, result in enumerate(formatted_results, 1):
                        response_text += f"{idx}. {result['title']} (PID: {result['pid']})\n"
                        
                        # Add CANSIM ID if available (useful for finding related data)
                        if result['cansim_id']:
                            response_text += f"   CANSIM ID: {result['cansim_id']}\n"
                            
                        # Add time range and frequency for context
                        response_text += f"   Time Range: {result['time_range']}\n"
                        response_text += f"   Frequency: {result['frequency']}\n"
                        response_text += f"   Last Updated: {result['release_time']}\n"
                        response_text += f"   Resource: {result['resource_uri']}\n\n"
                else:
                    response_text += ".\n\n"
                    
                    # Add search suggestions if available
                    if search_suggestions:
                        response_text += "Suggestions for finding relevant data:\n"
                        for idx, suggestion in enumerate(search_suggestions, 1):
                            response_text += f"{idx}. {suggestion}\n"
                        
                        # Add a note about vectorized search
                        response_text += "\nYou may also search for specific vectors if you know their IDs (e.g., 'v41690973' for CPI All-items)."
                
                # Add documentation reference
                if not formatted_results:
                    response_text += "\nFor more information about available datasets, visit Statistics Canada's data portal: https://www150.statcan.gc.ca/n1/en/type/data"
                
                return response_text
                
            except Exception as e:
                logger.error(f"Error in search_datasets: {e}")
                return f"Error searching datasets: {str(e)}"
        
        # Dataset metadata tool
        @self.app.tool()
        async def get_dataset_metadata(pid: str):
            """Get detailed metadata for a StatCan dataset."""
            logger.info(f"Getting metadata for dataset PID: '{pid}'")
            
            try:
                # Check cache first
                cache_key = f"metadata_{pid}"
                metadata = metadata_cache.get(cache_key)
                
                if metadata is None:
                    # Not in cache, fetch from API
                    metadata = await self.wds_client.get_cube_metadata(pid)
                    
                    if metadata.get("status") != "SUCCESS":
                        return f"Error fetching metadata: {metadata.get('object', 'Unknown error')}"
                    
                    # Cache the result
                    metadata_cache.set(cache_key, metadata)
                
                # Format metadata
                cube_metadata = metadata.get("object", {})
                
                # Get title using cubeTitleEn which is the correct field based on debug output
                cube_title = cube_metadata.get("cubeTitleEn", "Unknown")
                
                # Get other important metadata
                start_date = cube_metadata.get("cubeStartDate", "Unknown")
                end_date = cube_metadata.get("cubeEndDate", "Unknown")
                frequency = cube_metadata.get("frequencyCode", "Unknown")
                release_time = cube_metadata.get("releaseTime", "Unknown")
                
                # Get dimensions and notes
                dimensions = cube_metadata.get("dimension", [])
                notes = cube_metadata.get("footnote", [])
                
                # Format the response
                response_text = f"Metadata for Dataset: {cube_title} (PID: {pid})\n\n"
                response_text += f"Time Coverage: {start_date} to {end_date}\n"
                response_text += f"Last Updated: {release_time}\n"
                
                # Add frequency information
                freq_map = {
                    1: "Annual",
                    2: "Semi-annual",
                    4: "Quarterly",
                    6: "Monthly",
                    7: "Biweekly",
                    8: "Weekly",
                    9: "Daily",
                    0: "Unknown"
                }
                response_text += f"Frequency: {freq_map.get(frequency, 'Unknown')}\n\n"
                
                # Add dimensions
                response_text += "Dimensions:\n"
                for dim in dimensions:
                    dim_name = dim.get('dimensionNameEn', 'Unknown')
                    members = len(dim.get('member', []))
                    response_text += f"- {dim_name} ({members} members)\n"
                
                # Add notes if available (limit to first 3 for brevity)
                if notes:
                    response_text += "\nNotes:\n"
                    for note in notes[:3]:
                        note_text = note.get("footnoteEn", "")
                        if note_text:
                            # Truncate long notes
                            if len(note_text) > 100:
                                note_text = note_text[:97] + "..."
                            response_text += f"- {note_text}\n"
                    
                    if len(notes) > 3:
                        response_text += f"- ... and {len(notes) - 3} more notes\n"
                
                # Add resource link
                response_text += f"\nFor more details, access the full metadata at: statcan://metadata/{pid}"
                
                return response_text
                
            except Exception as e:
                logger.error(f"Error in get_dataset_metadata: {e}")
                return f"Error fetching dataset metadata: {str(e)}"
        
        # Time series data retrieval tool
        @self.app.tool()
        async def get_data_series(vectors: List[str], periods: int = 10):
            """Get time series data for specific vectors."""
            if not vectors:
                return "No vector IDs provided. Please specify at least one vector ID."
            
            logger.info(f"Getting data for vectors: {vectors}, periods: {periods}")
            
            try:
                # Check cache first
                cache_key = f"data_{'_'.join(vectors)}_{periods}"
                data = data_cache.get(cache_key)
                
                if data is None:
                    # Not in cache, fetch from API
                    data = await self.wds_client.get_data_from_vectors(vectors, periods)
                    
                    if data.get("status") != "SUCCESS":
                        return f"Error fetching data: {data.get('object', 'Unknown error')}"
                    
                    # Cache the result
                    data_cache.set(cache_key, data)
                
                # Format the data
                vector_data = data.get("object", [])
                
                # Ensure vector_data is always a list
                if not isinstance(vector_data, list):
                    vector_data = [vector_data]
                
                response_text = f"Time Series Data for {len(vectors)} vector(s), last {periods} periods:\n\n"
                
                for vector_item in vector_data:
                    # Extract vector ID
                    vector_id = vector_item.get("vectorId", "Unknown")
                    if vector_id == "Unknown" and "coordinate" in vector_item:
                        # Try to find the vector ID in the request vectors list
                        for v in vectors:
                            v_clean = v.lower().replace('v', '')
                            if v_clean in str(vector_item):
                                vector_id = v
                                break
                                
                    # Get metadata for this vector to find a title
                    series_metadata = None
                    try:
                        # Get the product ID to fetch metadata
                        product_id = vector_item.get("productId")
                        if product_id:
                            # Try to get metadata for the dataset
                            metadata_key = f"metadata_{product_id}"
                            series_metadata = metadata_cache.get(metadata_key)
                            
                            if series_metadata is None:
                                series_metadata = await self.wds_client.get_cube_metadata(str(product_id))
                                if series_metadata.get("status") == "SUCCESS":
                                    metadata_cache.set(metadata_key, series_metadata)
                    except Exception as metadata_err:
                        logger.warning(f"Failed to get series metadata: {metadata_err}")
                    
                    # Extract title with fallback to coordinate information
                    title = vector_item.get("SeriesTitleEn", "")
                    if not title and series_metadata and series_metadata.get("status") == "SUCCESS":
                        # Try to construct a title from metadata and coordinate
                        cube_metadata = series_metadata.get("object", {})
                        dataset_title = cube_metadata.get("cubeTitleEn", "")
                        coordinate = vector_item.get("coordinate", "")
                        
                        if dataset_title:
                            title = f"{dataset_title} - Vector {vector_id}"
                        else:
                            title = f"Vector {vector_id}"
                    elif not title:
                        title = f"Vector {vector_id} (Coordinate: {vector_item.get('coordinate', 'Unknown')})"
                    
                    response_text += f"{title}\n"
                    
                    # Format observations
                    observations = vector_item.get("vectorDataPoint", [])
                    
                    # Sort observations by date if possible
                    try:
                        observations = sorted(observations, key=lambda x: x.get("refPer", ""))
                    except Exception:
                        # If sorting fails, use as-is
                        pass
                    
                    # Calculate some basic statistics
                    values = []
                    for obs in observations:
                        try:
                            value = float(obs.get("value", "0"))
                            values.append(value)
                        except (ValueError, TypeError):
                            pass
                    
                    # Add observations
                    for obs in observations:
                        ref_period = obs.get("refPer", "")
                        value = obs.get("value", "")
                        response_text += f"  {ref_period}: {value}\n"
                    
                    # Add statistics if we have numeric values
                    if values:
                        avg_value = sum(values) / len(values)
                        min_value = min(values)
                        max_value = max(values)
                        
                        # Calculate trend (positive, negative, or stable)
                        trend = "Stable"
                        if len(values) >= 2:
                            if values[-1] > values[0] * 1.01:  # 1% increase threshold
                                trend = "Increasing"
                            elif values[-1] < values[0] * 0.99:  # 1% decrease threshold
                                trend = "Decreasing"
                        
                        response_text += f"\n  Statistics: Average: {avg_value:.2f}, Min: {min_value:.2f}, Max: {max_value:.2f}"
                        response_text += f"\n  Trend: {trend}\n"
                    
                    response_text += "\n"
                
                # Add resource links
                response_text += "Access full time series data at:\n"
                for vector in vectors:
                    response_text += f"- statcan://series/{vector}\n"
                
                return response_text
                
            except Exception as e:
                logger.error(f"Error in get_data_series: {e}")
                return f"Error fetching time series data: {str(e)}"
    
    def _register_resources(self):
        """Register MCP resources."""
        # Add static resources
        self.app.add_resource(
            mcp_types.Resource(
                uri="statcan://datasets",
                name="StatCan Datasets",
                description="Browse or search Statistics Canada datasets",
            )
        )
        
        # Create example resources
        self.app.add_resource(
            mcp_types.Resource(
                uri="statcan://datasets/example",
                name="Example StatCan Dataset",
                description="Example dataset to showcase the resource system",
            )
        )
        
        self.app.add_resource(
            mcp_types.Resource(
                uri="statcan://metadata/example",
                name="Example StatCan Metadata",
                description="Example metadata resource",
            )
        )
        
        self.app.add_resource(
            mcp_types.Resource(
                uri="statcan://series/example",
                name="Example StatCan Time Series",
                description="Example time series resource",
            )
        )
        
        logger.debug("Registered StatCan MCP resources")
        
        # Register resource handlers
        @self.app.resource("statcan://datasets/{pid}")
        async def get_dataset(pid: str):
            """Get dataset information by Product ID."""
            logger.info(f"Accessing dataset resource: {pid}")
            
            if pid == "example":
                return "This is an example dataset resource. Replace with a real Product ID to access actual data."
            
            try:
                # Get dataset metadata
                cache_key = f"metadata_{pid}"
                metadata = metadata_cache.get(cache_key)
                
                if metadata is None:
                    metadata = await self.wds_client.get_cube_metadata(pid)
                    
                    if metadata.get("status") == "SUCCESS":
                        metadata_cache.set(cache_key, metadata)
                
                if metadata and metadata.get("status") == "SUCCESS":
                    cube_metadata = metadata.get("object", {})
                    
                    # Get basic metadata
                    cube_title_en = cube_metadata.get("cubeTitleEn", "Unknown")
                    cansim_id = cube_metadata.get("cansimId", "")
                    freq_code = cube_metadata.get("frequencyCode", 0)
                    release_time = cube_metadata.get("releaseTime", "Unknown")
                    start_date = cube_metadata.get("cubeStartDate", "Unknown")
                    end_date = cube_metadata.get("cubeEndDate", "Unknown")
                    
                    # Get dimensions and notes
                    dimensions = cube_metadata.get("dimension", [])
                    notes = cube_metadata.get("footnote", [])
                    
                    # Format frequency as human-readable
                    freq_map = {
                        1: "Annual",
                        2: "Semi-annual",
                        4: "Quarterly",
                        6: "Monthly",
                        7: "Biweekly",
                        8: "Weekly",
                        9: "Daily",
                        0: "Unknown"
                    }
                    frequency = freq_map.get(freq_code, "Unknown")
                    
                    # Build a comprehensive dataset overview
                    content = f"## {cube_title_en}\n\n"
                    
                    # Basic information section
                    content += "### Dataset Information\n\n"
                    content += f"**Product ID:** {pid}\n"
                    if cansim_id:
                        content += f"**CANSIM ID:** {cansim_id}\n"
                    content += f"**Time Coverage:** {start_date} to {end_date}\n"
                    content += f"**Frequency:** {frequency}\n"
                    content += f"**Last Updated:** {release_time}\n\n"
                    
                    # Dimensions section with member counts
                    content += "### Dimensions\n\n"
                    if dimensions:
                        for dim in dimensions:
                            dim_name = dim.get("dimensionNameEn", "Unknown")
                            members = len(dim.get("member", []))
                            content += f"- **{dim_name}** ({members} members)\n"
                    else:
                        content += "No dimension information available.\n"
                    
                    # Notes section (first 3)
                    if notes:
                        content += "\n### Notes\n\n"
                        for i, note in enumerate(notes[:3], 1):
                            note_text = note.get("footnoteEn", "")
                            if note_text:
                                # Truncate long notes
                                if len(note_text) > 150:
                                    note_text = note_text[:147] + "..."
                                content += f"{i}. {note_text}\n"
                        
                        if len(notes) > 3:
                            content += f"... and {len(notes) - 3} more notes\n"
                    
                    # Sample vectors section if available
                    vectors = cube_metadata.get("vectorArray", [])
                    if vectors and len(vectors) > 0:
                        content += "\n### Sample Vectors\n\n"
                        # Show up to 5 vectors
                        for i, vector in enumerate(vectors[:5], 1):
                            vector_id = vector.get("vectorId", "Unknown")
                            content += f"- v{vector_id}\n"
                        
                        if len(vectors) > 5:
                            content += f"... and {len(vectors) - 5} more vectors\n"
                    
                    # Usage guidance
                    content += "\n### Usage\n\n"
                    content += f"- Use `get_dataset_metadata({pid})` for detailed metadata\n"
                    if vectors and len(vectors) > 0:
                        vector_example = f"v{vectors[0].get('vectorId', '')}"
                        content += f"- Use `get_data_series(['{vector_example}'])` to retrieve data for a specific vector\n"
                    content += "- Search related datasets with `search_datasets('KEYWORD')`\n"
                    
                    return content
                else:
                    return f"Dataset {pid} not found or error retrieving metadata."
            except Exception as e:
                logger.error(f"Error accessing dataset resource: {e}")
                return f"Error accessing dataset {pid}: {str(e)}"
        
        @self.app.resource("statcan://metadata/{pid}")
        async def get_metadata(pid: str):
            """Get detailed metadata for a dataset by Product ID."""
            logger.info(f"Accessing metadata resource: {pid}")
            
            if pid == "example":
                return "This is an example metadata resource. Replace with a real Product ID to access actual metadata."
            
            try:
                # Get detailed metadata
                cache_key = f"metadata_{pid}"
                metadata = metadata_cache.get(cache_key)
                
                if metadata is None:
                    metadata = await self.wds_client.get_cube_metadata(pid)
                    
                    if metadata.get("status") == "SUCCESS":
                        metadata_cache.set(cache_key, metadata)
                
                if metadata and metadata.get("status") == "SUCCESS":
                    # Format full metadata
                    cube_metadata = metadata.get("object", {})
                    
                    # Convert to pretty-printed JSON for now
                    # In a real implementation, this would be better formatted
                    return f"Full metadata for dataset {pid}:\n\n{cube_metadata}"
                else:
                    return f"Metadata for dataset {pid} not found or error retrieving it."
            except Exception as e:
                logger.error(f"Error accessing metadata resource: {e}")
                return f"Error accessing metadata for {pid}: {str(e)}"
        
        @self.app.resource("statcan://series/{vector}")
        async def get_series(vector: str):
            """Get time series data by Vector ID."""
            logger.info(f"Accessing series resource: {vector}")
            
            if vector == "example":
                return "This is an example time series resource. Replace with a real Vector ID to access actual data."
            
            try:
                # First get metadata about this vector
                vector_clean = vector.lower().replace('v', '')
                series_info = None
                
                try:
                    # Try to get additional metadata about this vector
                    series_info = await self.wds_client.get_series_info_from_vector(vector)
                except Exception as info_err:
                    logger.warning(f"Failed to get series info: {info_err}")
                
                # Get series data
                cache_key = f"data_{vector}_20"  # Expanded to 20 periods for better trend analysis
                data = data_cache.get(cache_key)
                
                if data is None:
                    data = await self.wds_client.get_data_from_vectors([vector], 20)
                    
                    if data.get("status") == "SUCCESS":
                        data_cache.set(cache_key, data)
                
                if data and data.get("status") == "SUCCESS":
                    vector_data = data.get("object", [])
                    
                    if not vector_data:
                        return f"No data found for vector {vector}."
                    
                    # Handle both list and single object formats
                    if isinstance(vector_data, list):
                        if len(vector_data) == 0:
                            return f"No data found for vector {vector}."
                        item = vector_data[0]
                    else:
                        item = vector_data
                    
                    # Get metadata from response
                    vector_id = item.get("vectorId", vector_clean)
                    title = item.get("SeriesTitleEn", "Unknown Series")
                    
                    # Try to get product metadata for more context
                    product_id = item.get("productId")
                    dataset_title = "Unknown Dataset"
                    frequency = "Unknown"
                    
                    if product_id:
                        # Try to get metadata for the dataset
                        metadata_key = f"metadata_{product_id}"
                        series_metadata = metadata_cache.get(metadata_key)
                        
                        if series_metadata is None:
                            series_metadata = await self.wds_client.get_cube_metadata(str(product_id))
                            if series_metadata.get("status") == "SUCCESS":
                                metadata_cache.set(metadata_key, series_metadata)
                                
                        if series_metadata and series_metadata.get("status") == "SUCCESS":
                            cube_metadata = series_metadata.get("object", {})
                            dataset_title = cube_metadata.get("cubeTitleEn", "Unknown Dataset")
                            
                            # Get frequency
                            freq_code = cube_metadata.get("frequencyCode", 0)
                            freq_map = {
                                1: "Annual",
                                2: "Semi-annual",
                                4: "Quarterly",
                                6: "Monthly",
                                7: "Biweekly",
                                8: "Weekly",
                                9: "Daily",
                                0: "Unknown"
                            }
                            frequency = freq_map.get(freq_code, "Unknown")
                    
                    # If title is still unknown but we have vector info
                    if title == "Unknown Series" and series_info and series_info.get("status") == "SUCCESS":
                        series_object = series_info.get("object", {})
                        if isinstance(series_object, list) and len(series_object) > 0:
                            series_object = series_object[0]
                        title = series_object.get("SeriesTitleEn", "Unknown Series")
                    
                    # If still no title but we have dataset title, construct one
                    if title == "Unknown Series" and dataset_title != "Unknown Dataset":
                        coordinate = item.get("coordinate", "")
                        if coordinate:
                            title = f"{dataset_title} - {coordinate}"
                        else:
                            title = f"{dataset_title} - Vector {vector}"
                    
                    # Create markdown formatted output
                    content = f"## {title}\n\n"
                    
                    # Add context information
                    content += "### Series Information\n\n"
                    content += f"**Vector ID:** {vector}\n"
                    if product_id:
                        content += f"**Dataset:** {dataset_title} (PID: {product_id})\n"
                    content += f"**Frequency:** {frequency}\n"
                    
                    # Extract coordinate info if available
                    coordinate = item.get("coordinate", "")
                    if coordinate:
                        content += f"**Coordinate:** {coordinate}\n"
                    
                    # Get observations and sort them
                    observations = item.get("vectorDataPoint", [])
                    try:
                        observations = sorted(observations, key=lambda x: x.get("refPer", ""))
                    except Exception:
                        pass
                    
                    # Calculate statistics
                    values = []
                    for obs in observations:
                        try:
                            value = float(obs.get("value", "0"))
                            values.append(value)
                        except (ValueError, TypeError):
                            pass
                    
                    # Add statistics section
                    if values:
                        avg_value = sum(values) / len(values)
                        min_value = min(values)
                        max_value = max(values)
                        current = values[-1] if values else 0
                        
                        content += f"\n### Statistics\n\n"
                        content += f"**Latest Value:** {current:.2f}\n"
                        content += f"**Average:** {avg_value:.2f}\n"
                        content += f"**Range:** {min_value:.2f} to {max_value:.2f}\n"
                        
                        # Calculate trend
                        if len(values) >= 2:
                            pct_change = ((values[-1] - values[0]) / values[0]) * 100
                            trend_text = "Stable"
                            if pct_change > 1:
                                trend_text = f"Increasing ({pct_change:.1f}%)"
                            elif pct_change < -1:
                                trend_text = f"Decreasing ({-pct_change:.1f}%)"
                            
                            content += f"**Trend:** {trend_text} over {len(values)} periods\n"
                    
                    # Add data points
                    content += f"\n### Data Points ({len(observations)} periods)\n\n"
                    content += "| Period | Value |\n"
                    content += "|--------|-------|\n"
                    for obs in observations:
                        ref_period = obs.get("refPer", "")
                        value = obs.get("value", "")
                        content += f"| {ref_period} | {value} |\n"
                    
                    # Add related information and usage
                    content += "\n### Related Information\n\n"
                    if product_id:
                        content += f"- Browse complete dataset: `statcan://datasets/{product_id}`\n"
                    content += f"- Get more periods: `get_data_series(['{vector}'], periods=50)`\n"
                    content += "- Compare with other vectors: `get_data_series(['v1', 'v2', 'v3'])`\n"
                    
                    return content
                else:
                    return f"Time series data for vector {vector} not found or error retrieving it."
            except Exception as e:
                logger.error(f"Error accessing series resource: {e}")
                return f"Error accessing time series data for {vector}: {str(e)}"
    
    # We don't need a custom run method anymore
    # FastMCP.run() is called directly from __main__.py

# Create a server instance
statcan_server = StatCanMCPServer()
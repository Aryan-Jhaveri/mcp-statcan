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
from src.cache import metadata_cache, data_cache, cube_cache, vector_cache, search_cache, preload_hot_cache
from src.integrations.integrations import MCPIntegrations
# We're now using function-based tools directly in the server class
# instead of importing class-based tools

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
        
        # Initialize integrations
        self.integrations = MCPIntegrations()
        
        # Register MCP handlers
        self._register_tools()
        self._register_resources()
        self._register_integration_tools()
        
        # Note: Preload hot cache will be done when the server starts running
        # This is commented out here to avoid issues during testing
        # asyncio.create_task(preload_hot_cache(self.wds_client))
        
        logger.info(f"Initialized StatCan MCP server '{name}' v{version}")
    
    def _register_tools(self):
        """Register MCP tools."""
        
        # Storage and analysis tools
        @self.app.tool()
        async def store_dataset(series_id: str, data: List[Dict[str, Any]], metadata: Dict[str, Any]) -> str:
            """Store a dataset in the persistent database for future use."""
            from src.integrations.data_storage import DataStorageIntegration
            storage = DataStorageIntegration()
            
            try:
                result = storage.store_time_series(
                    series_id=series_id,
                    data=data,
                    metadata=metadata
                )
                
                if result:
                    return f"Successfully stored dataset '{series_id}' with {len(data)} data points."
                else:
                    return f"Failed to store dataset '{series_id}'."
            except Exception as e:
                logger.error(f"Error in store_dataset tool: {e}")
                return f"Error storing dataset: {str(e)}"
            finally:
                storage.close()
                
        @self.app.tool()
        async def retrieve_dataset(series_id: str) -> Dict[str, Any]:
            """Retrieve a dataset from the persistent database."""
            from src.integrations.data_storage import DataStorageIntegration
            storage = DataStorageIntegration()
            
            try:
                data, metadata = storage.retrieve_time_series(series_id)
                
                if not data:
                    return {"error": f"Dataset '{series_id}' not found in the database."}
                
                return {
                    "metadata": metadata,
                    "data": data[:10],  # Only return the first 10 data points 
                    "total_points": len(data)
                }
            except Exception as e:
                logger.error(f"Error in retrieve_dataset tool: {e}")
                return {"error": f"Error retrieving dataset: {str(e)}"}
            finally:
                storage.close()
                
        @self.app.tool()
        async def analyze_dataset(series_id: str, analysis_type: str = "summary", params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
            """Analyze a dataset from the persistent database."""
            from src.integrations.data_storage import DataStorageIntegration
            storage = DataStorageIntegration()
            
            try:
                params = params or {}
                result = storage.run_analysis(
                    series_id=series_id,
                    analysis_type=analysis_type,
                    params=params
                )
                
                return result
            except Exception as e:
                logger.error(f"Error in analyze_dataset tool: {e}")
                return {"error": f"Error analyzing dataset: {str(e)}"}
            finally:
                storage.close()
                
        @self.app.tool()
        async def get_citation(pid: str, format: str = "apa") -> Dict[str, Any]:
            """Get a properly formatted citation for a Statistics Canada dataset."""
            try:
                # Get the metadata for this product ID
                metadata = await self.wds_client.get_cube_metadata(pid)
                
                if metadata.get("status") != "SUCCESS":
                    return {"error": f"Error retrieving metadata for PID {pid}"}
                
                cube_metadata = metadata.get("object", {})
                
                # Extract citation information
                title = cube_metadata.get("cubeTitleEn", "Unknown")
                release_time = cube_metadata.get("releaseTime", "Unknown")
                
                # Format release time for citation
                release_date = "Unknown date"
                if release_time:
                    try:
                        # If release_time is in ISO format, convert to a readable date
                        from datetime import datetime
                        release_date = datetime.fromisoformat(release_time.replace('Z', '+00:00')).strftime("%B %d, %Y")
                    except:
                        release_date = release_time
                
                # Format the citation based on the requested format
                format_lower = format.lower()
                
                if format_lower == "apa":
                    citation = f"Statistics Canada. ({release_date}). {title} (Table {pid}). Retrieved from https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid={pid}"
                elif format_lower == "mla":
                    citation = f"Statistics Canada. \"{title}.\" Table {pid}. Statistics Canada. {release_date}. Web."
                elif format_lower == "chicago":
                    citation = f"Statistics Canada. {release_date}. \"{title}.\" Table {pid}."
                else:
                    citation = f"Statistics Canada. ({release_date}). {title} (Table {pid}). Retrieved from https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid={pid}"
                
                # Include URL for any format
                url = f"https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid={pid}"
                
                # Build the response
                return {
                    "citation": citation,
                    "url": url,
                    "format": format,
                    "details": {
                        "title": title,
                        "release_date": release_date,
                        "product_id": pid
                    }
                }
            except Exception as e:
                logger.error(f"Error in get_citation tool: {e}")
                return {"error": f"Error generating citation: {str(e)}"}
                
        @self.app.tool()
        async def compare_datasets(primary_series_id: str, secondary_series_id: str, comparison_type: str = "correlation") -> Dict[str, Any]:
            """Compare two datasets from the persistent database."""
            from src.integrations.data_storage import DataStorageIntegration
            storage = DataStorageIntegration()
            
            try:
                # For correlation analysis
                if comparison_type == "correlation":
                    result = storage.run_analysis(
                        series_id=primary_series_id,
                        analysis_type="correlation",
                        params={"compare_with": secondary_series_id}
                    )
                    return result
                else:
                    return {"error": f"Comparison type '{comparison_type}' not yet implemented."}
            except Exception as e:
                logger.error(f"Error in compare_datasets tool: {e}")
                return {"error": f"Error comparing datasets: {str(e)}"}
            finally:
                storage.close()
                
        @self.app.tool()
        async def forecast_dataset(series_id: str, periods: int = 6, method: str = "exponential_smoothing", params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
            """Generate a forecast for a dataset from the persistent database."""
            from src.integrations.data_storage import DataStorageIntegration
            storage = DataStorageIntegration()
            
            try:
                params = params or {}
                params["periods"] = periods
                
                # Run the forecast analysis
                result = storage.run_analysis(
                    series_id=series_id,
                    analysis_type="forecast",
                    params=params
                )
                
                return result
            except Exception as e:
                logger.error(f"Error in forecast_dataset tool: {e}")
                return {"error": f"Error forecasting dataset: {str(e)}"}
            finally:
                storage.close()
                
        @self.app.tool()
        async def list_stored_datasets() -> Dict[str, Any]:
            """List all datasets stored in the persistent database."""
            from src.integrations.data_storage import DataStorageIntegration
            storage = DataStorageIntegration()
            
            try:
                conn = storage.connect()
                cursor = conn.cursor()
                
                cursor.execute("""
                SELECT id, title, start_date, end_date, last_updated 
                FROM time_series
                ORDER BY last_updated DESC
                """)
                
                datasets = []
                for row in cursor.fetchall():
                    series_id, title, start_date, end_date, last_updated = row
                    
                    # Get count of data points
                    cursor.execute("SELECT COUNT(*) FROM data_points WHERE series_id = ?", (series_id,))
                    count = cursor.fetchone()[0]
                    
                    datasets.append({
                        "id": series_id,
                        "title": title,
                        "start_date": start_date,
                        "end_date": end_date,
                        "last_updated": last_updated,
                        "data_points": count
                    })
                
                if not datasets:
                    return {"message": "No datasets found in the database."}
                
                return {"datasets": datasets}
            except Exception as e:
                logger.error(f"Error in list_stored_datasets tool: {e}")
                return {"error": f"Error listing datasets: {str(e)}"}
            finally:
                storage.close()
                
        @self.app.tool()
        async def track_figure(pid: str, figure_name: str, figure_description: str = "", vector_ids: List[str] = None) -> Dict[str, Any]:
            """Track and reference a figure created from Statistics Canada data."""
            vector_ids = vector_ids or []
            
            try:
                # Get the metadata for this product ID
                metadata = await self.wds_client.get_cube_metadata(pid)
                
                if metadata.get("status") != "SUCCESS":
                    return {"error": f"Error retrieving metadata for PID {pid}"}
                
                cube_metadata = metadata.get("object", {})
                
                # Extract information
                title = cube_metadata.get("cubeTitleEn", "Unknown")
                release_time = cube_metadata.get("releaseTime", "Unknown")
                
                # Format release time for citation
                release_date = "Unknown date"
                if release_time:
                    try:
                        # If release_time is in ISO format, convert to a readable date
                        from datetime import datetime
                        release_date = datetime.fromisoformat(release_time.replace('Z', '+00:00')).strftime("%B %d, %Y")
                    except:
                        release_date = release_time
                
                # Create figure reference
                figure_reference = {
                    "figure_name": figure_name,
                    "description": figure_description or f"Figure based on {title}",
                    "source_dataset": {
                        "title": title,
                        "pid": pid,
                        "release_date": release_date,
                        "url": f"https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid={pid}"
                    },
                    "vectors": vector_ids,
                    "citation": f"Source: Statistics Canada, {title} (Table {pid}), {release_date}."
                }
                
                # Create a user-friendly note about the figure
                note = f"""
Figure {figure_name} is based on Statistics Canada data from "{title}" (Table {pid}).
Source: Statistics Canada, Table {pid}, {release_date}.
URL: https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid={pid}
                """.strip()
                
                # Combine into final response
                return {
                    "figure_reference": figure_reference,
                    "note": note
                }
            except Exception as e:
                logger.error(f"Error in track_figure tool: {e}")
                return {"error": f"Error tracking figure: {str(e)}"}
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
            """Get time series data for specific vectors for the most recent periods."""
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
                    
                    # Extract product ID if possible - vector data is associated with a table
                    vector_item = next((v for v in vector_data if str(v.get("vectorId", "")).replace("v", "") == vector.replace("v", "")), None)
                    if vector_item and "productId" in vector_item:
                        pid = vector_item.get("productId")
                        # Format the PID to make sure it has 10 digits
                        if len(str(pid)) <= 8:  # 8-digit or shorter needs formatting
                            # The web URL format for tables requires 10 digits (pid with 8 digits + 01)
                            # Format: AAAAAAABB where AAAAAAAA is 8-digit PID and BB is 01
                            pid_str = str(pid).zfill(8) + "01"
                        else:
                            pid_str = str(pid)
                        response_text += f"  View online at: https://www150.statcan.gc.ca/t1/tbl1/en/cv.action?pid={pid_str}\n"
                
                # If we have a single vector with observations, add visualization suggestion
                if len(vector_data) == 1 and len(observations) > 1:
                    response_text += "\n### Visualization\n\n"
                    response_text += "To visualize this data, you can use the Vega-Lite MCP server with the following command:\n\n"
                    response_text += "```\nView result from create_chart from mcp-vegalite (isaacwasserman/mcp-vegalite-server) {\n"
                    response_text += "  \"data\": [\n"
                    
                    # Generate sample data in the format expected by Vega-Lite
                    for obs in observations:
                        ref_period = obs.get("refPer", "")
                        value = obs.get("value", "")
                        response_text += f"    {{\"date\": \"{ref_period}\", \"value\": {value}}},\n"
                    
                    # Remove trailing comma and close array
                    response_text = response_text[:-2] + "\n  ],\n"
                    
                    # Add visualization spec
                    response_text += "  \"mark\": \"line\",\n"
                    response_text += "  \"encoding\": {\n"
                    response_text += "    \"x\": {\"field\": \"date\", \"type\": \"temporal\", \"title\": \"Date\"},\n"
                    response_text += "    \"y\": {\"field\": \"value\", \"type\": \"quantitative\", \"title\": \"Value\"}\n"
                    response_text += "  },\n"
                    response_text += f"  \"title\": \"{title}\"\n"
                    response_text += "}\n```\n"
                    response_text += "\nYou can customize the chart type by changing 'mark' to 'bar', 'point', or 'area'."
                
                # If we have multiple vectors with observations, add multi-series visualization suggestion
                elif len(vector_data) > 1:
                    response_text += "\n### Multi-Series Visualization\n\n"
                    response_text += "To visualize multiple series, you can use the Vega-Lite MCP server with the following command:\n\n"
                    response_text += "```\nView result from create_chart from mcp-vegalite (isaacwasserman/mcp-vegalite-server) {\n"
                    response_text += "  \"data\": [\n"
                    
                    # Generate sample data for each vector
                    for i, item in enumerate(vector_data):
                        vector_id = item.get("vectorId", f"vector_{i}")
                        v_obs = item.get("vectorDataPoint", [])
                        
                        # Try to get a short title
                        v_title = title if i == 0 else f"Vector {vector_id}"
                        if len(v_title) > 30:
                            v_title = v_title[:27] + "..."
                        
                        for obs in v_obs:
                            ref_period = obs.get("refPer", "")
                            value = obs.get("value", "")
                            response_text += f"    {{\"date\": \"{ref_period}\", \"value\": {value}, \"series\": \"{v_title}\"}},\n"
                    
                    # Remove trailing comma and close array
                    response_text = response_text[:-2] + "\n  ],\n"
                    
                    # Add visualization spec for multi-series
                    response_text += "  \"mark\": \"line\",\n"
                    response_text += "  \"encoding\": {\n"
                    response_text += "    \"x\": {\"field\": \"date\", \"type\": \"temporal\", \"title\": \"Date\"},\n"
                    response_text += "    \"y\": {\"field\": \"value\", \"type\": \"quantitative\", \"title\": \"Value\"},\n"
                    response_text += "    \"color\": {\"field\": \"series\", \"type\": \"nominal\"}\n"
                    response_text += "  },\n"
                    response_text += f"  \"title\": \"Time Series Data from {start_date} to {end_date}\"\n"
                    response_text += "}\n```\n"
                    response_text += "\nYou can customize the chart type by changing 'mark' to 'bar', 'point', or 'area'."
                
                return response_text
                
            except Exception as e:
                logger.error(f"Error in get_data_series: {e}")
                return f"Error fetching time series data: {str(e)}"
        
        @self.app.tool()
        async def get_data_series_by_range(vectors: List[str], start_date: str, end_date: str = None):
            """Get time series data for specific vectors over a date range.
            
            Args:
                vectors: List of vector IDs to retrieve data for
                start_date: Start date in YYYY-MM-DD format
                end_date: End date in YYYY-MM-DD format (defaults to current date if not provided)
            """
            if not vectors:
                return "No vector IDs provided. Please specify at least one vector ID."
            
            # If end_date is not provided, use current date
            if end_date is None:
                from datetime import datetime
                end_date = datetime.now().strftime("%Y-%m-%d")
            
            logger.info(f"Getting data for vectors: {vectors}, date range: {start_date} to {end_date}")
            
            try:
                # Check cache first
                cache_key = f"range_data_{'_'.join(vectors)}_{start_date}_{end_date}"
                data = data_cache.get(cache_key)
                
                if data is None:
                    # Not in cache, fetch from API
                    if len(vectors) == 1:
                        # For a single vector, use the single vector endpoint
                        data = await self.wds_client.get_data_from_vector_by_range(vectors[0], start_date, end_date)
                    else:
                        # For multiple vectors, use the bulk endpoint
                        data = await self.wds_client.get_bulk_vector_data_by_range(vectors, start_date, end_date)
                    
                    if data.get("status") != "SUCCESS":
                        return f"Error fetching data: {data.get('object', 'Unknown error')}"
                    
                    # Cache the result
                    data_cache.set(cache_key, data)
                
                # Format the data
                vector_data = data.get("object", [])
                
                # Ensure vector_data is always a list
                if not isinstance(vector_data, list):
                    vector_data = [vector_data]
                
                response_text = f"Time Series Data for {len(vectors)} vector(s) from {start_date} to {end_date}:\n\n"
                
                for vector_item in vector_data:
                    # Extract vector ID and format similar to get_data_series
                    vector_id = vector_item.get("vectorId", "Unknown")
                    if vector_id == "Unknown" and "coordinate" in vector_item:
                        for v in vectors:
                            v_clean = v.lower().replace('v', '')
                            if v_clean in str(vector_item):
                                vector_id = v
                                break
                    
                    # Get title information
                    try:
                        # Try to get series info for a better title
                        series_info = await self.wds_client.get_series_info_from_vector(vector_id)
                        if series_info.get("status") == "SUCCESS":
                            info_obj = series_info.get("object", [])
                            if isinstance(info_obj, list) and info_obj:
                                title = info_obj[0].get("SeriesTitleEn", f"Vector {vector_id}")
                            else:
                                title = f"Vector {vector_id}"
                        else:
                            title = f"Vector {vector_id}"
                    except Exception:
                        title = f"Vector {vector_id}"
                    
                    response_text += f"{title}\n"
                    
                    # Format observations
                    observations = vector_item.get("vectorDataPoint", [])
                    
                    # Sort observations by date
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
                        
                        # Calculate trend and percent change
                        trend = "Stable"
                        pct_change = 0
                        if len(values) >= 2:
                            pct_change = ((values[-1] - values[0]) / values[0]) * 100
                            if pct_change > 1:  # 1% increase threshold
                                trend = f"Increasing ({pct_change:.1f}%)"
                            elif pct_change < -1:  # 1% decrease threshold
                                trend = f"Decreasing ({-pct_change:.1f}%)"
                        
                        response_text += f"\n  Statistics: Average: {avg_value:.2f}, Min: {min_value:.2f}, Max: {max_value:.2f}"
                        response_text += f"\n  Trend: {trend} over {len(observations)} periods\n"
                    
                    response_text += "\n"
                
                # Add resource links
                response_text += "Access full time series data at:\n"
                for vector in vectors:
                    response_text += f"- statcan://series/{vector}\n"
                    
                    # Extract product ID if possible - vector data is associated with a table
                    vector_item = next((v for v in vector_data if str(v.get("vectorId", "")).replace("v", "") == vector.replace("v", "")), None)
                    if vector_item and "productId" in vector_item:
                        pid = vector_item.get("productId")
                        # Format the PID to make sure it has 10 digits
                        if len(str(pid)) <= 8:  # 8-digit or shorter needs formatting
                            # The web URL format for tables requires 10 digits (pid with 8 digits + 01)
                            # Format: AAAAAAABB where AAAAAAAA is 8-digit PID and BB is 01
                            pid_str = str(pid).zfill(8) + "01"
                        else:
                            pid_str = str(pid)
                        response_text += f"  View online at: https://www150.statcan.gc.ca/t1/tbl1/en/cv.action?pid={pid_str}\n"
                
                # If we have a single vector with observations, add visualization suggestion
                if len(vector_data) == 1 and len(observations) > 1:
                    response_text += "\n### Visualization\n\n"
                    response_text += "To visualize this data, you can use the Vega-Lite MCP server with the following command:\n\n"
                    response_text += "```\nView result from create_chart from mcp-vegalite (isaacwasserman/mcp-vegalite-server) {\n"
                    response_text += "  \"data\": [\n"
                    
                    # Generate sample data in the format expected by Vega-Lite
                    for obs in observations:
                        ref_period = obs.get("refPer", "")
                        value = obs.get("value", "")
                        response_text += f"    {{\"date\": \"{ref_period}\", \"value\": {value}}},\n"
                    
                    # Remove trailing comma and close array
                    response_text = response_text[:-2] + "\n  ],\n"
                    
                    # Add visualization spec
                    response_text += "  \"mark\": \"line\",\n"
                    response_text += "  \"encoding\": {\n"
                    response_text += "    \"x\": {\"field\": \"date\", \"type\": \"temporal\", \"title\": \"Date\"},\n"
                    response_text += "    \"y\": {\"field\": \"value\", \"type\": \"quantitative\", \"title\": \"Value\"}\n"
                    response_text += "  },\n"
                    response_text += f"  \"title\": \"{title}\"\n"
                    response_text += "}\n```\n"
                    response_text += "\nYou can customize the chart type by changing 'mark' to 'bar', 'point', or 'area'."
                
                # If we have multiple vectors with observations, add multi-series visualization suggestion
                elif len(vector_data) > 1:
                    response_text += "\n### Multi-Series Visualization\n\n"
                    response_text += "To visualize multiple series, you can use the Vega-Lite MCP server with the following command:\n\n"
                    response_text += "```\nView result from create_chart from mcp-vegalite (isaacwasserman/mcp-vegalite-server) {\n"
                    response_text += "  \"data\": [\n"
                    
                    # Generate sample data for each vector
                    for i, item in enumerate(vector_data):
                        vector_id = item.get("vectorId", f"vector_{i}")
                        v_obs = item.get("vectorDataPoint", [])
                        
                        # Try to get a short title
                        v_title = title if i == 0 else f"Vector {vector_id}"
                        if len(v_title) > 30:
                            v_title = v_title[:27] + "..."
                        
                        for obs in v_obs:
                            ref_period = obs.get("refPer", "")
                            value = obs.get("value", "")
                            response_text += f"    {{\"date\": \"{ref_period}\", \"value\": {value}, \"series\": \"{v_title}\"}},\n"
                    
                    # Remove trailing comma and close array
                    response_text = response_text[:-2] + "\n  ],\n"
                    
                    # Add visualization spec for multi-series
                    response_text += "  \"mark\": \"line\",\n"
                    response_text += "  \"encoding\": {\n"
                    response_text += "    \"x\": {\"field\": \"date\", \"type\": \"temporal\", \"title\": \"Date\"},\n"
                    response_text += "    \"y\": {\"field\": \"value\", \"type\": \"quantitative\", \"title\": \"Value\"},\n"
                    response_text += "    \"color\": {\"field\": \"series\", \"type\": \"nominal\"}\n"
                    response_text += "  },\n"
                    response_text += f"  \"title\": \"Time Series Data from {start_date} to {end_date}\"\n"
                    response_text += "}\n```\n"
                    response_text += "\nYou can customize the chart type by changing 'mark' to 'bar', 'point', or 'area'."
                
                return response_text
                
            except Exception as e:
                logger.error(f"Error in get_data_series_by_range: {e}")
                return f"Error fetching time series data: {str(e)}"
                
        @self.app.tool()
        async def get_series_from_cube(product_id: str, coordinate: List[str], periods: int = 10):
            """Get time series data for a specific cube and coordinate.
            
            Args:
                product_id: StatCan Product ID (PID) for the cube
                coordinate: List of dimension member values that identify the series
                periods: Number of latest periods to retrieve
            """
            logger.info(f"Getting data for cube {product_id}, coordinate {coordinate}, periods: {periods}")
            
            try:
                # Validate and clean the coordinate
                if not isinstance(coordinate, list):
                    # If coordinate is a string, try to parse it as a list
                    try:
                        if isinstance(coordinate, str):
                            if "[" in coordinate:
                                # Looks like a JSON list
                                import json
                                coordinate = json.loads(coordinate)
                            else:
                                # Comma-separated values
                                coordinate = coordinate.split(",")
                    except Exception:
                        return "Invalid coordinate format. Please provide a list of dimension member values."
                
                # Check cache first
                cache_key = f"cube_data_{product_id}_{'-'.join(coordinate)}_{periods}"
                data = data_cache.get(cache_key)
                
                if data is None:
                    # Not in cache, fetch from API
                    data = await self.wds_client.get_data_from_cube_coordinate(product_id, coordinate, periods)
                    
                    if data.get("status") != "SUCCESS":
                        return f"Error fetching data: {data.get('object', 'Unknown error')}"
                    
                    # Cache the result
                    data_cache.set(cache_key, data)
                
                # Get metadata for this cube for better context
                metadata_key = f"metadata_{product_id}"
                metadata = metadata_cache.get(metadata_key)
                
                if metadata is None:
                    metadata = await self.wds_client.get_cube_metadata(product_id)
                    if metadata.get("status") == "SUCCESS":
                        metadata_cache.set(metadata_key, metadata)
                
                # Format the data - handle the object structure correctly
                data_obj = data.get("object", [])
                
                # Make sure we're working with the right data structure
                if isinstance(data_obj, list) and len(data_obj) > 0:
                    series_data = data_obj[0]
                else:
                    series_data = data_obj
                
                # Extract series information
                series_id = series_data.get("vectorId", "Unknown")
                coordinate_str = series_data.get("coordinate", coordinate)
                
                # Try to get a title
                title = None
                if metadata and metadata.get("status") == "SUCCESS":
                    cube_metadata = metadata.get("object", {})
                    
                    # Get the dataset title
                    dataset_title = cube_metadata.get("cubeTitleEn", "")
                    
                    # Try to get dimension names for the coordinate
                    dimensions = cube_metadata.get("dimension", [])
                    dimension_names = []
                    
                    if dimensions and len(dimensions) == len(coordinate):
                        for i, dim in enumerate(dimensions):
                            # Get the dimension name
                            dim_name = dim.get("dimensionNameEn", "")
                            
                            # Try to get the member name
                            members = dim.get("member", [])
                            member_name = None
                            
                            for member in members:
                                if member.get("memberId", "") == coordinate[i]:
                                    member_name = member.get("memberNameEn", "")
                                    break
                            
                            if dim_name and member_name:
                                dimension_names.append(f"{dim_name}: {member_name}")
                            elif dim_name:
                                dimension_names.append(f"{dim_name}: {coordinate[i]}")
                    
                    if dataset_title:
                        if dimension_names:
                            title = f"{dataset_title} - {', '.join(dimension_names)}"
                        else:
                            title = f"{dataset_title} - Coordinate {coordinate_str}"
                
                if not title:
                    title = f"Data for Cube {product_id}, Coordinate {coordinate_str}"
                
                # Format observations
                observations = series_data.get("vectorDataPoint", [])
                
                # Sort observations by date
                try:
                    observations = sorted(observations, key=lambda x: x.get("refPer", ""))
                except Exception:
                    # If sorting fails, use as-is
                    pass
                
                response_text = f"{title}\n\n"
                
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
                    response_text += f"{ref_period}: {value}\n"
                
                # Add statistics if we have numeric values
                if values:
                    avg_value = sum(values) / len(values)
                    min_value = min(values)
                    max_value = max(values)
                    
                    # Calculate trend and percent change
                    trend = "Stable"
                    pct_change = 0
                    if len(values) >= 2:
                        pct_change = ((values[-1] - values[0]) / values[0]) * 100
                        if pct_change > 1:  # 1% increase threshold
                            trend = f"Increasing ({pct_change:.1f}%)"
                        elif pct_change < -1:  # 1% decrease threshold
                            trend = f"Decreasing ({-pct_change:.1f}%)"
                    
                    response_text += f"\nStatistics:\n"
                    response_text += f"Average: {avg_value:.2f}\n"
                    response_text += f"Range: {min_value:.2f} to {max_value:.2f}\n"
                    response_text += f"Trend: {trend} over {len(observations)} periods\n"
                
                # Add resource link if vector ID is available
                if series_id != "Unknown":
                    response_text += f"\nAccess full time series data at: statcan://series/{series_id}\n"
                    
                    # Format the PID to ensure proper URL format
                    pid_str = product_id
                    if len(product_id) <= 8:  # 8-digit or shorter needs formatting
                        # The web URL format for tables requires 10 digits (pid with 8 digits + 01)
                        # Format: AAAAAAABB where AAAAAAAA is 8-digit PID and BB is 01
                        pid_str = str(product_id).zfill(8) + "01"
                    
                    response_text += f"View online at: https://www150.statcan.gc.ca/t1/tbl1/en/cv.action?pid={pid_str}\n"
                
                # Add visualization suggestion if we have data points
                if observations and len(observations) > 1:
                    response_text += "\n### Visualization\n\n"
                    response_text += "To visualize this data, you can use the Vega-Lite MCP server with the following command:\n\n"
                    response_text += "```\nView result from create_chart from mcp-vegalite (isaacwasserman/mcp-vegalite-server) {\n"
                    response_text += "  \"data\": [\n"
                    
                    # Generate sample data in the format expected by Vega-Lite
                    for obs in observations:
                        ref_period = obs.get("refPer", "")
                        value = obs.get("value", "")
                        response_text += f"    {{\"date\": \"{ref_period}\", \"value\": {value}}},\n"
                    
                    # Remove trailing comma and close array
                    response_text = response_text[:-2] + "\n  ],\n"
                    
                    # Add visualization spec
                    response_text += "  \"mark\": \"line\",\n"
                    response_text += "  \"encoding\": {\n"
                    response_text += "    \"x\": {\"field\": \"date\", \"type\": \"temporal\", \"title\": \"Date\"},\n"
                    response_text += "    \"y\": {\"field\": \"value\", \"type\": \"quantitative\", \"title\": \"Value\"}\n"
                    response_text += "  },\n"
                    response_text += f"  \"title\": \"{title}\"\n"
                    response_text += "}\n```\n"
                    response_text += "\nYou can customize the chart type by changing 'mark' to 'bar', 'point', or 'area'."
                
                return response_text
                
            except Exception as e:
                logger.error(f"Error in get_series_from_cube: {e}")
                return f"Error fetching series data: {str(e)}"
                
        @self.app.tool()
        async def get_download_link(product_id: str, format_type: str = "csv"):
            """Get a download link for a complete StatCan table.
            
            Args:
                product_id: StatCan Product ID (PID) for the cube
                format_type: Format type, either "csv" (default) or "sdmx"
            """
            logger.info(f"Getting download link for cube {product_id} in {format_type} format")
            
            try:
                # Validate format type
                if format_type.lower() not in ["csv", "sdmx"]:
                    return "Invalid format type. Please choose either 'csv' or 'sdmx'."
                
                # Get the download URL
                url = await self.wds_client.get_full_table_download_url(product_id, format_type)
                
                # Get basic metadata about this dataset
                metadata_key = f"metadata_{product_id}"
                metadata = metadata_cache.get(metadata_key)
                
                if metadata is None:
                    metadata = await self.wds_client.get_cube_metadata(product_id)
                    if metadata.get("status") == "SUCCESS":
                        metadata_cache.set(metadata_key, metadata)
                
                # Get dataset title for better context
                title = "dataset"
                if metadata and metadata.get("status") == "SUCCESS":
                    cube_metadata = metadata.get("object", {})
                    title = cube_metadata.get("cubeTitleEn", "dataset")
                
                response_text = f"Download link for {title}:\n\n"
                response_text += f"{url}\n\n"
                
                response_text += "Note: This link provides the complete dataset in "
                if format_type.lower() == "csv":
                    response_text += "CSV format (comma-separated values), suitable for importing into spreadsheets or data analysis tools."
                else:
                    response_text += "SDMX format (Statistical Data and Metadata Exchange), an ISO standard format for statistical data exchange."
                
                return response_text
                
            except Exception as e:
                logger.error(f"Error in get_download_link: {e}")
                return f"Error generating download link: {str(e)}"
                
        @self.app.tool()
        async def get_recently_updated_datasets(days: int = 7, max_results: int = 10):
            """Get a list of recently updated datasets.
            
            Args:
                days: Number of days to look back for updates (default: 7)
                max_results: Maximum number of results to return (default: 10)
            """
            logger.info(f"Getting datasets updated in the last {days} days")
            
            try:
                # Check cache first
                cache_key = f"changed_cubes_{days}"
                data = metadata_cache.get(cache_key)
                
                if data is None:
                    # Not in cache, fetch from API
                    data = await self.wds_client.get_changed_cube_list(days)
                    
                    if data.get("status") != "SUCCESS":
                        return f"Error fetching updated datasets: {data.get('object', 'Unknown error')}"
                    
                    # Cache the result
                    metadata_cache.set(cache_key, data)
                
                # Format the data
                cubes = data.get("object", [])
                
                # Limit results
                cubes = cubes[:max_results]
                
                response_text = f"Datasets updated in the last {days} days:\n\n"
                
                if not cubes:
                    response_text += "No datasets were updated in this time period."
                    return response_text
                
                # Format results
                for idx, cube in enumerate(cubes, 1):
                    title = cube.get("cubeTitleEn", cube.get("productTitle", "Unknown"))
                    pid = cube.get("productId", "")
                    release_time = cube.get("releaseTime", "Unknown")
                    
                    response_text += f"{idx}. {title} (PID: {pid})\n"
                    response_text += f"   Updated: {release_time}\n"
                    response_text += f"   Resource: statcan://datasets/{pid}\n\n"
                
                return response_text
                
            except Exception as e:
                logger.error(f"Error in get_recently_updated_datasets: {e}")
                return f"Error fetching recently updated datasets: {str(e)}"
    
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
    
    def _register_integration_tools(self):
        """Register MCP tools for integrations with other MCP servers."""
        
        @self.app.tool()
        async def get_dataset_visualization(pid: str, chart_type: str = "line"):
            """Get visualization code for a StatCan dataset.
            
            Args:
                pid: StatCan Product ID (PID)
                chart_type: Type of chart to create (line, bar, area)
            """
            logger.info(f"Getting visualization for dataset {pid} with chart type {chart_type}")
            
            try:
                # Get the dataset metadata
                metadata_key = f"metadata_{pid}"
                metadata = metadata_cache.get(metadata_key)
                
                if metadata is None:
                    metadata = await self.wds_client.get_cube_metadata(pid)
                    if metadata.get("status") == "SUCCESS":
                        metadata_cache.set(metadata_key, metadata)
                
                if metadata and metadata.get("status") == "SUCCESS":
                    # Get dataset info
                    cube_metadata = metadata.get("object", {})
                    title = cube_metadata.get("cubeTitleEn", f"Dataset {pid}")
                    start_date = cube_metadata.get("cubeStartDate", "")
                    end_date = cube_metadata.get("cubeEndDate", "")
                    
                    # Try to get a sample vector from this dataset
                    vectors = cube_metadata.get("vectorArray", [])
                    if vectors and len(vectors) > 0:
                        # Get the first vector's data
                        vector_id = vectors[0].get("vectorId", "")
                        vector_data = await self.wds_client.get_data_from_vectors([f"v{vector_id}"], 10)
                        
                        if vector_data.get("status") == "SUCCESS":
                            # Extract data points
                            data_object = vector_data.get("object", [])
                            if isinstance(data_object, list) and len(data_object) > 0:
                                observations = data_object[0].get("vectorDataPoint", [])
                                
                                # Create data points for visualization
                                data_points = []
                                for obs in observations:
                                    ref_period = obs.get("refPer", "")
                                    value = obs.get("value", "")
                                    data_points.append({"date": ref_period, "value": value})
                                
                                # Create dataset info
                                dataset_info = {
                                    "pid": pid,
                                    "title": title,
                                    "time_range": f"{start_date} to {end_date}"
                                }
                                
                                # Generate visualization command
                                viz_suggestions = self.integrations.generate_visualization_suggestions(
                                    dataset_info, data_points
                                )
                                
                                # Return the appropriate chart type
                                if chart_type == "bar":
                                    return viz_suggestions.get("line_chart", "").replace("\"line\"", "\"bar\"")
                                elif chart_type == "area":
                                    return viz_suggestions.get("line_chart", "").replace("\"line\"", "\"area\"")
                                else:
                                    return viz_suggestions.get("line_chart", "")
                    
                    # If we couldn't get vector data, return a general message
                    return (
                        "To visualize this dataset, you need to retrieve specific vector data first "
                        "using the get_data_series tool, then use the isaacwasserman/mcp-vegalite-server "
                        "for visualization."
                    )
                else:
                    return f"Error retrieving dataset metadata for PID {pid}"
            except Exception as e:
                logger.error(f"Error in get_dataset_visualization: {e}")
                return f"Error generating visualization: {str(e)}"
                
        @self.app.tool()
        async def analyze_dataset(pid: str, analysis_type: str = "trends"):
            """Get advanced analysis for a StatCan dataset.
            
            Args:
                pid: StatCan Product ID (PID)
                analysis_type: Type of analysis (trends, growth_rates, seasonality, outliers)
            """
            logger.info(f"Analyzing dataset {pid} with analysis type {analysis_type}")
            
            try:
                # Get the dataset metadata
                metadata_key = f"metadata_{pid}"
                metadata = metadata_cache.get(metadata_key)
                
                if metadata is None:
                    metadata = await self.wds_client.get_cube_metadata(pid)
                    if metadata.get("status") == "SUCCESS":
                        metadata_cache.set(metadata_key, metadata)
                
                if metadata and metadata.get("status") == "SUCCESS":
                    # Get dataset info
                    cube_metadata = metadata.get("object", {})
                    title = cube_metadata.get("cubeTitleEn", f"Dataset {pid}")
                    
                    # Try to get a sample vector from this dataset
                    vectors = cube_metadata.get("vectorArray", [])
                    if vectors and len(vectors) > 0:
                        # Get the first vector's data
                        vector_id = vectors[0].get("vectorId", "")
                        vector_data = await self.wds_client.get_data_from_vectors([f"v{vector_id}"], 20)
                        
                        if vector_data.get("status") == "SUCCESS":
                            # Extract data points
                            data_object = vector_data.get("object", [])
                            if isinstance(data_object, list) and len(data_object) > 0:
                                observations = data_object[0].get("vectorDataPoint", [])
                                
                                # Create data points for analysis
                                data_points = []
                                for obs in observations:
                                    data_points.append(obs)
                                
                                # Create dataset info
                                dataset_info = {
                                    "pid": pid,
                                    "title": title,
                                }
                                
                                # Generate analysis command
                                analysis_suggestions = self.integrations.generate_analysis_suggestions(
                                    dataset_info, data_points
                                )
                                
                                # Return the appropriate analysis
                                return analysis_suggestions.get(analysis_type, 
                                    analysis_suggestions.get("trends", "No analysis available"))
                    
                    # If we couldn't get vector data, return a general message
                    return (
                        "To analyze this dataset, you need to retrieve specific vector data first "
                        "using the get_data_series tool, then use specialized analysis tools."
                    )
                else:
                    return f"Error retrieving dataset metadata for PID {pid}"
            except Exception as e:
                logger.error(f"Error in analyze_dataset: {e}")
                return f"Error generating analysis: {str(e)}"
                
        @self.app.tool()
        async def deep_research_dataset(pid: str, research_focus: str = None):
            """Get deep research context for a StatCan dataset.
            
            Args:
                pid: StatCan Product ID (PID)
                research_focus: Specific focus for the research
            """
            logger.info(f"Performing deep research on dataset {pid} with focus {research_focus}")
            
            try:
                # Get the dataset metadata
                metadata_key = f"metadata_{pid}"
                metadata = metadata_cache.get(metadata_key)
                
                if metadata is None:
                    metadata = await self.wds_client.get_cube_metadata(pid)
                    if metadata.get("status") == "SUCCESS":
                        metadata_cache.set(metadata_key, metadata)
                
                if metadata and metadata.get("status") == "SUCCESS":
                    # Get dataset info
                    cube_metadata = metadata.get("object", {})
                    title = cube_metadata.get("cubeTitleEn", f"Dataset {pid}")
                    start_date = cube_metadata.get("cubeStartDate", "")
                    end_date = cube_metadata.get("cubeEndDate", "")
                    freq_code = cube_metadata.get("frequencyCode", 0)
                    
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
                    frequency = freq_map.get(freq_code, "Unknown")
                    
                    # Get dimensions
                    dimensions = []
                    for dim in cube_metadata.get("dimension", []):
                        dim_name = dim.get("dimensionNameEn", "")
                        if dim_name:
                            dimensions.append(dim_name)
                    
                    # Create dataset info
                    dataset_info = {
                        "pid": pid,
                        "title": title,
                        "description": title,  # Use title as description if none available
                        "time_range": f"{start_date} to {end_date}",
                        "frequency": frequency,
                        "dimensions": dimensions
                    }
                    
                    # Try to get a sample of data
                    data_points = []
                    vectors = cube_metadata.get("vectorArray", [])
                    if vectors and len(vectors) > 0:
                        # Get the first vector's data
                        vector_id = vectors[0].get("vectorId", "")
                        vector_data = await self.wds_client.get_data_from_vectors([f"v{vector_id}"], 5)
                        
                        if vector_data.get("status") == "SUCCESS":
                            data_object = vector_data.get("object", [])
                            if isinstance(data_object, list) and len(data_object) > 0:
                                observations = data_object[0].get("vectorDataPoint", [])
                                data_points = observations
                    
                    # Generate deep research command
                    from src.integrations.deep_research import DeepResearchIntegration
                    research_command = DeepResearchIntegration.get_deep_research_command(
                        dataset_info, data_points, research_focus
                    )
                    
                    return research_command
                else:
                    return f"Error retrieving dataset metadata for PID {pid}"
            except Exception as e:
                logger.error(f"Error in deep_research_dataset: {e}")
                return f"Error generating deep research: {str(e)}"
        
        @self.app.tool()
        async def explore_dataset(pid: str):
            """Get data exploration options for a StatCan dataset.
            
            Args:
                pid: StatCan Product ID (PID)
            """
            logger.info(f"Exploring dataset {pid}")
            
            try:
                # Get the dataset metadata
                metadata_key = f"metadata_{pid}"
                metadata = metadata_cache.get(metadata_key)
                
                if metadata is None:
                    metadata = await self.wds_client.get_cube_metadata(pid)
                    if metadata.get("status") == "SUCCESS":
                        metadata_cache.set(metadata_key, metadata)
                
                if metadata and metadata.get("status") == "SUCCESS":
                    # Get dataset info
                    cube_metadata = metadata.get("object", {})
                    title = cube_metadata.get("cubeTitleEn", f"Dataset {pid}")
                    start_date = cube_metadata.get("cubeStartDate", "")
                    end_date = cube_metadata.get("cubeEndDate", "")
                    
                    # Get dimensions
                    dimensions = []
                    for dim in cube_metadata.get("dimension", []):
                        dim_name = dim.get("dimensionNameEn", "")
                        members = len(dim.get("member", []))
                        if dim_name:
                            dimensions.append(f"{dim_name} ({members} members)")
                    
                    # Get sample data
                    data_sample = []
                    vectors = cube_metadata.get("vectorArray", [])
                    if vectors and len(vectors) > 0:
                        # Get the first vector's data
                        vector_id = vectors[0].get("vectorId", "")
                        vector_data = await self.wds_client.get_data_from_vectors([f"v{vector_id}"], 5)
                        
                        if vector_data.get("status") == "SUCCESS":
                            data_object = vector_data.get("object", [])
                            if isinstance(data_object, list) and len(data_object) > 0:
                                observations = data_object[0].get("vectorDataPoint", [])
                                data_sample = observations
                    
                    # Create dataset info
                    dataset_info = {
                        "pid": pid,
                        "title": title,
                        "time_range": f"{start_date} to {end_date}",
                        "dimensions": dimensions
                    }
                    
                    # Format the dataset summary with integration options
                    summary = self.integrations.format_dataset_summary(
                        dataset_info, data_sample, include_integrations=True
                    )
                    
                    return summary
                else:
                    return f"Error retrieving dataset metadata for PID {pid}"
            except Exception as e:
                logger.error(f"Error in explore_dataset: {e}")
                return f"Error exploring dataset: {str(e)}"
    
    # We don't need a custom run method anymore
    # FastMCP.run() is called directly from __main__.py

# Create a server instance
statcan_server = StatCanMCPServer()
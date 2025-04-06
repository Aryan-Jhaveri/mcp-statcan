"""
Main MCP server implementation for StatCan Web Data Service.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

import mcp.types as mcp_types
from mcp.server import Server

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
        self.app = Server(name, version=version)
        self.wds_client = WDSClient()
        
        # Register MCP handlers
        self._register_tools()
        self._register_resources()
        
        logger.info(f"Initialized StatCan MCP server '{name}' v{version}")
    
    def _register_tools(self):
        """Register MCP tools."""
        # Dataset search tool
        @self.app.tool(
            name="search_datasets",
            description="Search for StatCan datasets by keywords, themes, or geography",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search terms to find datasets"
                    },
                    "theme": {
                        "type": "string",
                        "description": "Filter by theme (e.g., 'economy', 'health')",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
        )
        async def search_datasets(request):
            """Search for StatCan datasets."""
            query = request.get("query", "")
            theme = request.get("theme", "")
            max_results = request.get("max_results", 10)
            
            logger.info(f"Searching datasets with query: '{query}', theme: '{theme}'")
            
            try:
                search_results = await self.wds_client.search_cubes(query)
                
                if search_results.get("status") != "SUCCESS":
                    return {
                        "isError": True,
                        "content": [
                            {
                                "type": "text",
                                "text": f"Error searching datasets: {search_results.get('object', 'Unknown error')}"
                            }
                        ]
                    }
                
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
                
                # Format results
                formatted_results = []
                for dataset in results:
                    product_id = dataset.get("productId", "")
                    title = dataset.get("cubeTitleEn", dataset.get("productTitle", "Unknown"))
                    release_time = dataset.get("releaseTime", "Unknown")
                    
                    formatted_results.append({
                        "pid": product_id,
                        "title": title,
                        "release_time": release_time,
                        "resource_uri": f"statcan://datasets/{product_id}"
                    })
                
                response_text = f"Found {len(formatted_results)} datasets matching '{query}'"
                if theme:
                    response_text += f" with theme '{theme}'"
                
                if formatted_results:
                    response_text += ":\n\n"
                    for idx, result in enumerate(formatted_results, 1):
                        response_text += (
                            f"{idx}. {result['title']} (PID: {result['pid']})\n"
                            f"   Released: {result['release_time']}\n"
                            f"   Resource: {result['resource_uri']}\n\n"
                        )
                else:
                    response_text += "."
                
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": response_text,
                        }
                    ]
                }
                
            except Exception as e:
                logger.error(f"Error in search_datasets: {e}")
                return {
                    "isError": True,
                    "content": [
                        {
                            "type": "text",
                            "text": f"Error searching datasets: {str(e)}"
                        }
                    ]
                }
        
        # Dataset metadata tool
        @self.app.tool(
            name="get_dataset_metadata",
            description="Get detailed metadata for a StatCan dataset",
            input_schema={
                "type": "object",
                "properties": {
                    "pid": {
                        "type": "string",
                        "description": "Product ID (PID) for the dataset"
                    },
                },
                "required": ["pid"],
            },
        )
        async def get_dataset_metadata(request):
            """Get metadata for a specific dataset."""
            pid = request.get("pid", "")
            
            logger.info(f"Getting metadata for dataset PID: '{pid}'")
            
            try:
                # Check cache first
                cache_key = f"metadata_{pid}"
                metadata = metadata_cache.get(cache_key)
                
                if metadata is None:
                    # Not in cache, fetch from API
                    metadata = await self.wds_client.get_cube_metadata(pid)
                    
                    if metadata.get("status") != "SUCCESS":
                        return {
                            "isError": True,
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"Error fetching metadata: {metadata.get('object', 'Unknown error')}"
                                }
                            ]
                        }
                    
                    # Cache the result
                    metadata_cache.set(cache_key, metadata)
                
                # Format metadata
                cube_metadata = metadata.get("object", {})
                
                cube_title = cube_metadata.get("cubeTitle", "Unknown")
                dimensions = cube_metadata.get("dimension", [])
                notes = cube_metadata.get("footnote", [])
                
                response_text = f"Metadata for Dataset: {cube_title} (PID: {pid})\n\n"
                
                # Add dimensions
                response_text += "Dimensions:\n"
                for dim in dimensions:
                    dim_name = dim.get("dimensionNameEn", "Unknown")
                    response_text += f"- {dim_name}\n"
                
                # Add notes if available
                if notes:
                    response_text += "\nNotes:\n"
                    for note in notes:
                        note_text = note.get("footnoteEn", "")
                        if note_text:
                            response_text += f"- {note_text}\n"
                
                # Add resource link
                response_text += f"\nFor more details, access the full metadata at: statcan://metadata/{pid}"
                
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": response_text,
                        }
                    ]
                }
                
            except Exception as e:
                logger.error(f"Error in get_dataset_metadata: {e}")
                return {
                    "isError": True,
                    "content": [
                        {
                            "type": "text",
                            "text": f"Error fetching dataset metadata: {str(e)}"
                        }
                    ]
                }
        
        # Time series data retrieval tool
        @self.app.tool(
            name="get_data_series",
            description="Get time series data for specific vectors",
            input_schema={
                "type": "object",
                "properties": {
                    "vectors": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of vector IDs to retrieve"
                    },
                    "periods": {
                        "type": "integer",
                        "description": "Number of periods to retrieve",
                        "default": 10,
                    },
                },
                "required": ["vectors"],
            },
        )
        async def get_data_series(request):
            """Get time series data for specific vectors."""
            vectors = request.get("vectors", [])
            periods = request.get("periods", 10)
            
            if not vectors:
                return {
                    "isError": True,
                    "content": [
                        {
                            "type": "text",
                            "text": "No vector IDs provided. Please specify at least one vector ID."
                        }
                    ]
                }
            
            logger.info(f"Getting data for vectors: {vectors}, periods: {periods}")
            
            try:
                # Check cache first
                cache_key = f"data_{'_'.join(vectors)}_{periods}"
                data = data_cache.get(cache_key)
                
                if data is None:
                    # Not in cache, fetch from API
                    data = await self.wds_client.get_data_from_vectors(vectors, periods)
                    
                    if data.get("status") != "SUCCESS":
                        return {
                            "isError": True,
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"Error fetching data: {data.get('object', 'Unknown error')}"
                                }
                            ]
                        }
                    
                    # Cache the result
                    data_cache.set(cache_key, data)
                
                # Format the data
                vector_data = data.get("object", [])
                
                response_text = f"Time Series Data for {len(vectors)} vector(s), last {periods} periods:\n\n"
                
                for vector_item in vector_data:
                    vector_id = vector_item.get("vectorId", "Unknown")
                    title = vector_item.get("SeriesTitleEn", "Unknown Series")
                    response_text += f"Vector {vector_id}: {title}\n"
                    
                    observations = vector_item.get("vectorDataPoint", [])
                    for obs in observations:
                        ref_period = obs.get("refPer", "")
                        value = obs.get("value", "")
                        response_text += f"  {ref_period}: {value}\n"
                    
                    response_text += "\n"
                
                # Add resource links
                response_text += "Access full time series data at:\n"
                for vector in vectors:
                    response_text += f"- statcan://series/{vector}\n"
                
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": response_text,
                        }
                    ]
                }
                
            except Exception as e:
                logger.error(f"Error in get_data_series: {e}")
                return {
                    "isError": True,
                    "content": [
                        {
                            "type": "text",
                            "text": f"Error fetching time series data: {str(e)}"
                        }
                    ]
                }
    
    def _register_resources(self):
        """Register MCP resources."""
        @self.app.list_resources()
        async def list_resources():
            """List available resources."""
            # For now, return a simple static list
            # In a full implementation, this would be more dynamic
            resources = [
                mcp_types.Resource(
                    uri="statcan://datasets",
                    name="StatCan Datasets",
                    description="Browse or search Statistics Canada datasets",
                ),
                mcp_types.ResourceTemplate(
                    uriTemplate="statcan://datasets/{pid}",
                    name="StatCan Dataset",
                    description="Access a specific Statistics Canada dataset by Product ID (PID)",
                ),
                mcp_types.ResourceTemplate(
                    uriTemplate="statcan://metadata/{pid}",
                    name="StatCan Dataset Metadata",
                    description="Access metadata for a Statistics Canada dataset by Product ID (PID)",
                ),
                mcp_types.ResourceTemplate(
                    uriTemplate="statcan://series/{vector}",
                    name="StatCan Time Series",
                    description="Access a specific time series by Vector ID",
                ),
            ]
            
            logger.debug(f"Listed {len(resources)} resources")
            return resources
        
        @self.app.read_resource()
        async def read_resource(uri: str):
            """Read a resource."""
            logger.info(f"Reading resource: {uri}")
            
            try:
                # Parse URI
                if uri.startswith("statcan://datasets/"):
                    # Dataset resource
                    pid = uri.replace("statcan://datasets/", "")
                    
                    if not pid:
                        # List all datasets (placeholder - would be paginated in real implementation)
                        return "Statistics Canada Datasets\n\nUse the search_datasets tool to find specific datasets."
                    
                    # Get dataset metadata
                    cache_key = f"metadata_{pid}"
                    metadata = metadata_cache.get(cache_key)
                    
                    if metadata is None:
                        metadata = await self.wds_client.get_cube_metadata(pid)
                        
                        if metadata.get("status") == "SUCCESS":
                            metadata_cache.set(cache_key, metadata)
                    
                    if metadata and metadata.get("status") == "SUCCESS":
                        cube_metadata = metadata.get("object", {})
                        
                        cube_title = cube_metadata.get("cubeTitle", "Unknown")
                        cube_title_en = cube_metadata.get("cubeTitleEn", cube_title)
                        freq_code = cube_metadata.get("frequencyCode", "Unknown")
                        release_time = cube_metadata.get("releaseTime", "Unknown")
                        dimensions = cube_metadata.get("dimension", [])
                        
                        content = f"Dataset: {cube_title_en} (PID: {pid})\n\n"
                        content += f"Frequency: {freq_code}\n"
                        content += f"Last Release: {release_time}\n\n"
                        
                        content += "Dimensions:\n"
                        for dim in dimensions:
                            dim_name = dim.get("dimensionNameEn", "Unknown")
                            content += f"- {dim_name}\n"
                        
                        content += "\nUse the get_dataset_metadata tool for more details."
                        
                        return content
                    else:
                        return f"Dataset {pid} not found or error retrieving metadata."
                
                elif uri.startswith("statcan://metadata/"):
                    # Metadata resource
                    pid = uri.replace("statcan://metadata/", "")
                    
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
                
                elif uri.startswith("statcan://series/"):
                    # Time series resource
                    vector = uri.replace("statcan://series/", "")
                    
                    # Get series data
                    cache_key = f"data_{vector}_10"  # Default to 10 periods
                    data = data_cache.get(cache_key)
                    
                    if data is None:
                        data = await self.wds_client.get_data_from_vectors([vector], 10)
                        
                        if data.get("status") == "SUCCESS":
                            data_cache.set(cache_key, data)
                    
                    if data and data.get("status") == "SUCCESS":
                        vector_data = data.get("object", [])
                        
                        if not vector_data:
                            return f"No data found for vector {vector}."
                        
                        item = vector_data[0]
                        vector_id = item.get("vectorId", "Unknown")
                        title = item.get("SeriesTitleEn", "Unknown Series")
                        
                        content = f"Time Series: {title} (Vector: {vector_id})\n\n"
                        
                        observations = item.get("vectorDataPoint", [])
                        content += "Observations:\n"
                        for obs in observations:
                            ref_period = obs.get("refPer", "")
                            value = obs.get("value", "")
                            content += f"{ref_period}: {value}\n"
                        
                        content += "\nUse the get_data_series tool to retrieve more periods or multiple vectors."
                        
                        return content
                    else:
                        return f"Time series data for vector {vector} not found or error retrieving it."
                
                else:
                    return f"Resource not found: {uri}"
                
            except Exception as e:
                logger.error(f"Error reading resource {uri}: {e}")
                return f"Error reading resource {uri}: {str(e)}"
    
    async def run(self, input_stream, output_stream, initialization_options=None):
        """Run the MCP server.
        
        Args:
            input_stream: Input stream for MCP communication
            output_stream: Output stream for MCP communication
            initialization_options: Initialization options
        """
        if initialization_options is None:
            initialization_options = self.app.create_initialization_options()
        
        logger.info(f"Starting StatCan MCP server '{self.name}' v{self.version}")
        
        try:
            await self.app.run(
                input_stream,
                output_stream,
                initialization_options
            )
        finally:
            # Clean up resources
            await self.wds_client.close()
            metadata_cache.close()
            data_cache.close()
            
            logger.info(f"StatCan MCP server '{self.name}' v{self.version} stopped")

# Create a server instance
statcan_server = StatCanMCPServer()
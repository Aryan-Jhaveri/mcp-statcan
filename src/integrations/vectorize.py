"""
Integration with the vectorize-io/vectorize-mcp-server MCP server.

This module provides functionality for semantic search and embeddings functionality
using the vectorize-io/vectorize-mcp-server MCP server.
"""

import logging
import json
from typing import List, Dict, Any, Optional, Union

logger = logging.getLogger(__name__)

class VectorizeIntegration:
    """Integration with the vectorize-io/vectorize-mcp-server MCP server."""
    
    @staticmethod
    def format_dataset_for_indexing(
        pid: str,
        title: str,
        description: str,
        time_range: str = "",
        frequency: str = "",
        dimensions: List[str] = None,
        vectors: List[str] = None
    ) -> Dict[str, Any]:
        """
        Format a dataset for indexing in the vectorize server.
        
        Args:
            pid: Dataset Product ID
            title: Dataset title
            description: Dataset description
            time_range: Time range of the dataset
            frequency: Update frequency
            dimensions: List of dimensions in the dataset
            vectors: List of vector IDs in the dataset
            
        Returns:
            Formatted dataset document
        """
        # Create a document with the dataset information
        document = {
            "id": f"statcan_dataset_{pid}",
            "text": "",
            "metadata": {
                "pid": pid,
                "title": title,
                "time_range": time_range,
                "frequency": frequency,
                "source": "Statistics Canada",
                "type": "dataset"
            }
        }
        
        # Create the text content
        text = f"# {title}\n\n"
        text += f"Product ID: {pid}\n"
        if time_range:
            text += f"Time Range: {time_range}\n"
        if frequency:
            text += f"Frequency: {frequency}\n"
        text += "\n"
        
        # Add description
        text += "## Description\n\n"
        text += f"{description}\n\n"
        
        # Add dimensions if provided
        if dimensions:
            text += "## Dimensions\n\n"
            for dim in dimensions:
                text += f"- {dim}\n"
            text += "\n"
        
        # Add vectors if provided
        if vectors:
            text += "## Available Vectors\n\n"
            for vec in vectors[:10]:  # Limit to first 10
                text += f"- {vec}\n"
            if len(vectors) > 10:
                text += f"- ... and {len(vectors) - 10} more vectors\n"
        
        document["text"] = text
        return document
    
    @staticmethod
    def generate_dataset_index_config(datasets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate configuration for indexing datasets in the vectorize server.
        
        Args:
            datasets: List of datasets to index
            
        Returns:
            Configuration for the vectorize server
        """
        # Format each dataset for indexing
        documents = []
        for dataset in datasets:
            document = VectorizeIntegration.format_dataset_for_indexing(
                pid=dataset.get("pid", ""),
                title=dataset.get("title", ""),
                description=dataset.get("description", ""),
                time_range=dataset.get("time_range", ""),
                frequency=dataset.get("frequency", ""),
                dimensions=dataset.get("dimensions", []),
                vectors=dataset.get("vectors", [])
            )
            documents.append(document)
        
        # Create the configuration
        config = {
            "index_name": "statcan_datasets",
            "documents": documents,
            "overwrite": False
        }
        
        return config
    
    @staticmethod
    def generate_search_config(query: str, filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Generate configuration for searching datasets in the vectorize server.
        
        Args:
            query: Search query
            filters: Filters to apply to the search
            
        Returns:
            Configuration for the vectorize server
        """
        # Build metadata filter if provided
        filter_expr = None
        if filters:
            filter_conditions = []
            
            # Time range filter
            if "start_year" in filters and "end_year" in filters:
                # Special handling for time range filter
                # (This is simplified and would need to be adapted for the actual API)
                time_range = f"{filters['start_year']}-{filters['end_year']}"
                filter_conditions.append({
                    "field": "metadata.time_range",
                    "operator": "contains",
                    "value": time_range
                })
            
            # Frequency filter
            if "frequency" in filters:
                filter_conditions.append({
                    "field": "metadata.frequency",
                    "operator": "equals",
                    "value": filters["frequency"]
                })
            
            # Dataset type filter - always true for StatCan datasets
            filter_conditions.append({
                "field": "metadata.source",
                "operator": "equals",
                "value": "Statistics Canada"
            })
            
            # Combine conditions
            if filter_conditions:
                filter_expr = {"and": filter_conditions}
        
        # Create the configuration
        config = {
            "index_name": "statcan_datasets",
            "query": query,
            "top_k": 5,
        }
        
        # Add filter if provided
        if filter_expr:
            config["filter"] = filter_expr
        
        return config
    
    @staticmethod
    def get_index_datasets_command(datasets: List[Dict[str, Any]]) -> str:
        """
        Generate a command for indexing datasets in the vectorize server.
        
        Args:
            datasets: List of datasets to index
            
        Returns:
            Command string for indexing datasets
        """
        config = VectorizeIntegration.generate_dataset_index_config(datasets)
        
        # Create a JSON-formatted string (pretty-printed for readability)
        config_json = json.dumps(config, indent=2)
        
        # Generate the command
        command = (
            f"View result from create_or_update_index from vectorize (vectorize-io/vectorize-mcp-server) "
            f"{config_json}"
        )
        
        return command
    
    @staticmethod
    def get_search_datasets_command(query: str, filters: Dict[str, Any] = None) -> str:
        """
        Generate a command for searching datasets in the vectorize server.
        
        Args:
            query: Search query
            filters: Filters to apply to the search
            
        Returns:
            Command string for searching datasets
        """
        config = VectorizeIntegration.generate_search_config(query, filters)
        
        # Create a JSON-formatted string (pretty-printed for readability)
        config_json = json.dumps(config, indent=2)
        
        # Generate the command
        command = (
            f"View result from search from vectorize (vectorize-io/vectorize-mcp-server) "
            f"{config_json}"
        )
        
        return command
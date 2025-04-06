"""
Main integrations module that brings together all MCP server integrations.

This module provides a unified interface for working with various MCP server integrations.
"""

import logging
from typing import List, Dict, Any, Optional, Union

from .data_exploration import DataExplorationIntegration
from .sql_analyzer import SQLAnalyzerIntegration
from .deep_research import DeepResearchIntegration
from .vectorize import VectorizeIntegration

logger = logging.getLogger(__name__)

class MCPIntegrations:
    """Main integrations class for the StatCan MCP server."""
    
    @staticmethod
    def generate_visualization_suggestions(
        dataset_info: Dict[str, Any],
        data_points: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """
        Generate visualization suggestions for the dataset.
        
        Args:
            dataset_info: Information about the dataset
            data_points: Data points from the dataset
            
        Returns:
            Dictionary of visualization types and their MCP commands
        """
        title = dataset_info.get("title", "StatCan Dataset")
        
        # Generate suggestions
        suggestions = {}
        
        # Add line chart for time series
        suggestions["line_chart"] = (
            f"```\nView result from create_chart from mcp-vegalite (isaacwasserman/mcp-vegalite-server) {{\n"
            f"  \"data\": [ /* Include your time series data here */ ],\n"
            f"  \"mark\": \"line\",\n"
            f"  \"encoding\": {{\n"
            f"    \"x\": {{\"field\": \"date\", \"type\": \"temporal\", \"title\": \"Date\"}},\n"
            f"    \"y\": {{\"field\": \"value\", \"type\": \"quantitative\", \"title\": \"Value\"}}\n"
            f"  }},\n"
            f"  \"title\": \"{title}\"\n"
            f"}}\n```"
        )
        
        # Add data exploration
        suggestions["data_exploration"] = DataExplorationIntegration.get_exploration_command(
            data_points, title=title
        )
        
        # Add SQL analysis
        suggestions["sql_analysis"] = SQLAnalyzerIntegration.get_sql_analysis_command(
            data_points, query_type="trends"
        )
        
        return suggestions
    
    @staticmethod
    def generate_analysis_suggestions(
        dataset_info: Dict[str, Any],
        data_points: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """
        Generate analysis suggestions for the dataset.
        
        Args:
            dataset_info: Information about the dataset
            data_points: Data points from the dataset
            
        Returns:
            Dictionary of analysis types and their MCP commands
        """
        title = dataset_info.get("title", "StatCan Dataset")
        
        # Generate suggestions
        suggestions = {}
        
        # Add basic trends analysis
        suggestions["trends"] = SQLAnalyzerIntegration.get_sql_analysis_command(
            data_points, query_type="trends"
        )
        
        # Add growth rate analysis
        suggestions["growth_rates"] = SQLAnalyzerIntegration.get_sql_analysis_command(
            data_points, query_type="growth_rates"
        )
        
        # Add moving average analysis
        suggestions["moving_average"] = SQLAnalyzerIntegration.get_sql_analysis_command(
            data_points, query_type="moving_average"
        )
        
        # Add seasonality analysis
        suggestions["seasonality"] = SQLAnalyzerIntegration.get_sql_analysis_command(
            data_points, query_type="seasonality"
        )
        
        # Add percentiles analysis
        suggestions["percentiles"] = SQLAnalyzerIntegration.get_sql_analysis_command(
            data_points, query_type="percentiles"
        )
        
        # Add outliers analysis
        suggestions["outliers"] = SQLAnalyzerIntegration.get_sql_analysis_command(
            data_points, query_type="outliers"
        )
        
        return suggestions
    
    @staticmethod
    def get_exploration_options(dataset_info: Dict[str, Any]) -> Dict[str, str]:
        """
        Get exploration options for the dataset.
        
        Args:
            dataset_info: Information about the dataset
            
        Returns:
            Dictionary of exploration options and their descriptions
        """
        # Create exploration options
        options = {
            "visualization": "Generate visualizations for this dataset",
            "analysis": "Perform statistical analysis on this dataset",
            "deep_research": "Conduct deep research on this topic with additional context",
            "semantic_search": "Search for related datasets on this topic"
        }
        
        return options
    
    @staticmethod
    def format_dataset_summary(
        dataset_info: Dict[str, Any],
        data_sample: List[Dict[str, Any]],
        include_integrations: bool = True
    ) -> str:
        """
        Format a summary of the dataset with integration suggestions.
        
        Args:
            dataset_info: Information about the dataset
            data_sample: Sample data points from the dataset
            include_integrations: Whether to include integration suggestions
            
        Returns:
            Formatted dataset summary
        """
        title = dataset_info.get("title", "StatCan Dataset")
        pid = dataset_info.get("pid", "")
        time_range = dataset_info.get("time_range", "")
        dimensions = dataset_info.get("dimensions", [])
        
        # Format the summary
        summary = f"# {title}\n\n"
        summary += f"Product ID: {pid}\n"
        if time_range:
            summary += f"Time Range: {time_range}\n"
        summary += "\n"
        
        # Add data sample
        if data_sample:
            summary += "## Data Sample\n\n"
            summary += "```\n"
            for i, point in enumerate(data_sample[:5]):  # Limit to 5 samples
                if "refPer" in point and "value" in point:
                    summary += f"{point['refPer']}: {point['value']}\n"
                elif "date" in point and "value" in point:
                    summary += f"{point['date']}: {point['value']}\n"
            summary += "```\n\n"
        
        # Add dimension info
        if dimensions:
            summary += "## Dimensions\n\n"
            for dim in dimensions[:3]:  # Limit to 3 dimensions
                summary += f"- {dim}\n"
            if len(dimensions) > 3:
                summary += f"- ... and {len(dimensions) - 3} more dimensions\n"
            summary += "\n"
        
        # Add integration suggestions
        if include_integrations:
            summary += "## Available Integrations\n\n"
            summary += "You can explore this dataset further using these MCP integrations:\n\n"
            summary += "### Visualization\n"
            summary += "Use the isaacwasserman/mcp-vegalite-server to create interactive visualizations\n\n"
            
            summary += "### Data Exploration\n"
            summary += "Use the reading-plus-ai/mcp-server-data-exploration to discover patterns\n\n"
            
            summary += "### SQL Analysis\n"
            summary += "Use the j4c0bs/mcp-server-sql-analyzer to perform advanced SQL queries\n\n"
            
            summary += "### Deep Research\n"
            summary += "Use the reading-plus-ai/mcp-server-deep-research to get deeper context\n\n"
        
        return summary
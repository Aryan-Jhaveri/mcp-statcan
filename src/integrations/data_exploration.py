"""
Integration with the reading-plus-ai/mcp-server-data-exploration MCP server.

This module provides functionality for data exploration and analysis using 
the reading-plus-ai/mcp-server-data-exploration MCP server.
"""

import logging
import json
import pandas as pd
from typing import List, Dict, Any, Optional, Union

logger = logging.getLogger(__name__)

class DataExplorationIntegration:
    """Integration with the reading-plus-ai/mcp-server-data-exploration MCP server."""
    
    @staticmethod
    def prepare_csv_data(data: List[Dict[str, Any]], title: str = "StatCan Dataset") -> str:
        """
        Convert time series data to CSV format for the data exploration MCP server.
        
        Args:
            data: List of data points, each with date and value
            title: Title of the dataset
            
        Returns:
            CSV representation of the data
        """
        if not data:
            return "date,value\n"
        
        # Create a DataFrame from the data
        try:
            # Extract the data points
            rows = []
            for item in data:
                if "date" in item and "value" in item:
                    rows.append({"date": item["date"], "value": item["value"]})
                elif "refPer" in item and "value" in item:
                    rows.append({"date": item["refPer"], "value": item["value"]})
            
            if not rows:
                return "date,value\n"
                
            df = pd.DataFrame(rows)
            
            # Convert to CSV
            csv_data = df.to_csv(index=False)
            return csv_data
        except Exception as e:
            logger.error(f"Error converting data to CSV: {e}")
            return "date,value\n"
    
    @staticmethod
    def get_data_exploration_prompt(
        data_format: str = "csv", 
        title: str = "StatCan Dataset", 
        analysis_type: str = "general"
    ) -> str:
        """
        Generate a prompt for the data exploration MCP server.
        
        Args:
            data_format: Format of the data ('csv' or 'json')
            title: Title of the dataset
            analysis_type: Type of analysis to perform (general, trends, seasonal, etc.)
            
        Returns:
            Prompt for the data exploration MCP server
        """
        exploration_prompts = {
            "general": (
                f"Analyze this {data_format} dataset from Statistics Canada titled '{title}'. "
                "Provide a comprehensive summary of the data including:\n"
                "1. Basic statistics (mean, median, min, max, etc.)\n"
                "2. Trend analysis - is the data increasing, decreasing, or stable over time?\n"
                "3. Notable patterns or anomalies\n"
                "4. Key insights about what this data reveals\n"
                "5. Recommendations for further analysis\n\n"
                "Format your response with clear headings and concise explanations."
            ),
            "trends": (
                f"Analyze this {data_format} dataset from Statistics Canada titled '{title}' "
                "focusing specifically on trends over time. Identify:\n"
                "1. The overall trend direction (increasing, decreasing, stable, cyclical)\n"
                "2. Rate of change (how quickly values are changing)\n"
                "3. Any trend reversals or inflection points\n"
                "4. Comparison of recent trends vs historical patterns\n"
                "5. Potential seasonal or cyclical patterns\n\n"
                "Include quantitative measures such as growth rates or percentage changes when relevant."
            ),
            "seasonal": (
                f"Perform a seasonal analysis on this {data_format} dataset from Statistics Canada "
                f"titled '{title}'. Identify:\n"
                "1. Whether seasonal patterns exist in the data\n"
                "2. The nature and strength of any seasonal effects\n"
                "3. Which months or quarters show the highest and lowest values\n"
                "4. Whether the seasonal patterns have remained consistent over time\n"
                "5. How the seasonal component might be separated from the overall trend\n\n"
                "Include specific examples from the data to illustrate your findings."
            ),
            "outliers": (
                f"Analyze this {data_format} dataset from Statistics Canada titled '{title}' "
                "focusing on outliers and anomalies. Identify:\n"
                "1. Any significant outliers in the data\n"
                "2. The magnitude and direction of these outliers\n"
                "3. When these outliers occurred (dates/times)\n"
                "4. Possible explanations for these anomalies based on known events\n"
                "5. Whether these outliers should be considered legitimate data points or potential errors\n\n"
                "Provide context for why these values might differ from the expected pattern."
            ),
            "comparative": (
                f"Perform a comparative analysis on this {data_format} dataset from Statistics Canada "
                f"titled '{title}'.\n"
                "If the data contains multiple series or categories, compare them across:\n"
                "1. Central tendencies (mean, median) and dispersion (standard deviation, range)\n"
                "2. Growth rates and volatility\n"
                "3. Correlation between different series\n"
                "4. Relative performance over different time periods\n"
                "5. Notable convergence or divergence points\n\n"
                "If this is a single time series, compare different time periods such as years, "
                "quarters, or before/after significant events."
            )
        }
        
        # Default to general analysis if the specified type is not available
        return exploration_prompts.get(analysis_type.lower(), exploration_prompts["general"])
    
    @staticmethod
    def generate_exploration_config(
        data: List[Dict[str, Any]], 
        title: str = "StatCan Dataset",
        analysis_type: str = "general"
    ) -> Dict[str, Any]:
        """
        Generate configuration for the data exploration MCP server.
        
        Args:
            data: List of data points, each with date and value
            title: Title of the dataset
            analysis_type: Type of analysis to perform
            
        Returns:
            Configuration for the data exploration MCP server
        """
        # Convert data to CSV
        csv_data = DataExplorationIntegration.prepare_csv_data(data, title)
        
        # Generate the prompt
        prompt = DataExplorationIntegration.get_data_exploration_prompt("csv", title, analysis_type)
        
        # Create the configuration
        config = {
            "file_content": csv_data,
            "file_name": f"{title.replace(' ', '_')}.csv",
            "prompt": prompt
        }
        
        return config
    
    @staticmethod
    def get_exploration_command(
        data: List[Dict[str, Any]], 
        title: str = "StatCan Dataset",
        analysis_type: str = "general"
    ) -> str:
        """
        Generate a command for using the data exploration MCP server.
        
        Args:
            data: List of data points, each with date and value
            title: Title of the dataset
            analysis_type: Type of analysis to perform
            
        Returns:
            Command string for using the data exploration MCP server
        """
        config = DataExplorationIntegration.generate_exploration_config(data, title, analysis_type)
        
        # Create a JSON-formatted string (pretty-printed for readability)
        config_json = json.dumps(config, indent=2)
        
        # Generate the command
        command = (
            f"View result from explore_data from mcp-data-exploration (reading-plus-ai/mcp-server-data-exploration) "
            f"{config_json}"
        )
        
        return command
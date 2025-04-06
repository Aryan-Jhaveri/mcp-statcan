"""
Integration with the reading-plus-ai/mcp-server-deep-research MCP server.

This module provides functionality for deep research and context on statistical data
using the reading-plus-ai/mcp-server-deep-research MCP server.
"""

import logging
import json
from typing import List, Dict, Any, Optional, Union

logger = logging.getLogger(__name__)

class DeepResearchIntegration:
    """Integration with the reading-plus-ai/mcp-server-deep-research MCP server."""
    
    @staticmethod
    def format_dataset_context(
        title: str,
        description: str,
        time_range: str,
        dimensions: List[str],
        source: str = "Statistics Canada"
    ) -> str:
        """
        Format dataset context information for the deep research server.
        
        Args:
            title: Dataset title
            description: Dataset description
            time_range: Time range of the dataset
            dimensions: List of dimensions in the dataset
            source: Data source
            
        Returns:
            Formatted context information
        """
        # Create a context document with the dataset information
        context = f"# {title}\n\n"
        context += f"Source: {source}\n\n"
        context += f"Time Range: {time_range}\n\n"
        
        context += "## Description\n\n"
        context += f"{description}\n\n"
        
        if dimensions:
            context += "## Dimensions\n\n"
            for dim in dimensions:
                context += f"- {dim}\n"
        
        return context
    
    @staticmethod
    def generate_research_questions(
        title: str,
        topic: str = None,
        time_range: str = None,
        geo_focus: str = "Canada"
    ) -> List[str]:
        """
        Generate research questions based on the dataset.
        
        Args:
            title: Dataset title
            topic: Specific topic to focus on
            time_range: Time range for questions
            geo_focus: Geographic focus
            
        Returns:
            List of research questions
        """
        # Extract a simpler topic if none provided
        if not topic:
            # Try to extract a topic from the title
            topic_keywords = ["employment", "unemployment", "inflation", "CPI", "GDP", 
                             "housing", "population", "income", "trade", "health",
                             "education", "environment", "crime", "migration"]
            
            for keyword in topic_keywords:
                if keyword.lower() in title.lower():
                    topic = keyword
                    break
            
            if not topic:
                topic = "economic indicators"
        
        # Create context-specific questions
        questions = [
            f"What are the key trends in {topic} in {geo_focus} {time_range or 'over time'}?",
            f"How does {topic} in {geo_focus} compare to historical averages?",
            f"What factors might explain changes in {topic} in {geo_focus} {time_range or 'recently'}?",
            f"How does {geo_focus}'s {topic} compare with other countries or regions?",
            f"What are the implications of these {topic} trends for {geo_focus}'s economy and policy?",
            f"What methodological considerations should be noted when interpreting this data?"
        ]
        
        return questions
    
    @staticmethod
    def generate_deep_research_config(
        dataset_info: Dict[str, Any],
        data_points: List[Dict[str, Any]] = None,
        research_focus: str = None
    ) -> Dict[str, Any]:
        """
        Generate configuration for the deep research MCP server.
        
        Args:
            dataset_info: Information about the dataset
            data_points: Sample data points from the dataset
            research_focus: Specific focus for the research
            
        Returns:
            Configuration for the deep research MCP server
        """
        # Extract dataset information
        title = dataset_info.get("title", "StatCan Dataset")
        description = dataset_info.get("description", "Statistical data from Statistics Canada")
        time_range = dataset_info.get("time_range", "")
        dimensions = dataset_info.get("dimensions", [])
        
        # Format the context
        context = DeepResearchIntegration.format_dataset_context(
            title, description, time_range, dimensions
        )
        
        # Generate research questions
        questions = DeepResearchIntegration.generate_research_questions(
            title, 
            topic=research_focus,
            time_range=time_range
        )
        
        # Format data sample if provided
        data_sample = ""
        if data_points and len(data_points) > 0:
            data_sample = "## Data Sample\n\n"
            data_sample += "```\n"
            for i, point in enumerate(data_points[:10]):  # Limit to 10 samples
                data_sample += f"{i+1}. "
                if "refPer" in point and "value" in point:
                    data_sample += f"{point['refPer']}: {point['value']}\n"
                elif "date" in point and "value" in point:
                    data_sample += f"{point['date']}: {point['value']}\n"
                else:
                    data_sample += f"{point}\n"
            data_sample += "```\n"
        
        # Combine context and data sample
        full_context = context + "\n\n" + data_sample
        
        # Create the configuration
        config = {
            "context": full_context,
            "question": f"Analyze this {research_focus or 'statistical'} data from Statistics Canada and provide insights.",
            "suggested_questions": questions,
            "search_depth": 3
        }
        
        return config
    
    @staticmethod
    def get_deep_research_command(
        dataset_info: Dict[str, Any],
        data_points: List[Dict[str, Any]] = None,
        research_focus: str = None
    ) -> str:
        """
        Generate a command for using the deep research MCP server.
        
        Args:
            dataset_info: Information about the dataset
            data_points: Sample data points from the dataset
            research_focus: Specific focus for the research
            
        Returns:
            Command string for using the deep research MCP server
        """
        config = DeepResearchIntegration.generate_deep_research_config(
            dataset_info,
            data_points,
            research_focus
        )
        
        # Create a JSON-formatted string (pretty-printed for readability)
        config_json = json.dumps(config, indent=2)
        
        # Generate the command
        command = (
            f"View result from research from mcp-deep-research (reading-plus-ai/mcp-server-deep-research) "
            f"{config_json}"
        )
        
        return command
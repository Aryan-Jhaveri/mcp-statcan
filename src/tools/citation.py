"""
MCP tools for StatCan data citations.

This module implements MCP tools for generating proper citations
for Statistics Canada datasets.
"""

import logging
import json
from typing import Dict, Any
import asyncio

from mcp.server.fastmcp.tools.base import BaseTool
from mcp.types import RenderableResponse
from pydantic import BaseModel, Field

from src.wds_client import WDSClient

logger = logging.getLogger(__name__)

class GetCitationConfig(BaseModel):
    """Configuration for the get_citation tool."""
    
    pid: str = Field(..., description="StatCan Product ID (PID)")
    format: str = Field("apa", description="Citation format (apa, mla, chicago)")

class GetCitationTool(BaseTool[GetCitationConfig]):
    """Tool for generating citations for StatCan data."""
    
    name = "get_citation"
    description = "Get a properly formatted citation for a Statistics Canada dataset"
    config_model = GetCitationConfig
    
    async def execute(self, config: GetCitationConfig) -> RenderableResponse:
        """Execute the get_citation tool."""
        client = WDSClient()
        
        try:
            # Get the metadata for this product ID
            metadata = await client.get_cube_metadata(config.pid)
            
            if metadata.get("status") \!= "SUCCESS":
                return RenderableResponse(
                    content=f"Error retrieving metadata for PID {config.pid}: {metadata.get('object', 'Unknown error')}",
                    media_type="text/plain"
                )
            
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
            format_lower = config.format.lower()
            
            if format_lower == "apa":
                citation = f"Statistics Canada. ({release_date}). {title} (Table {config.pid}). Retrieved from https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid={config.pid}"
            elif format_lower == "mla":
                citation = f"Statistics Canada. \"{title}.\" Table {config.pid}. Statistics Canada. {release_date}. Web."
            elif format_lower == "chicago":
                citation = f"Statistics Canada. {release_date}. \"{title}.\" Table {config.pid}."
            else:
                citation = f"Statistics Canada. ({release_date}). {title} (Table {config.pid}). Retrieved from https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid={config.pid}"
            
            # Include URL for any format
            url = f"https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid={config.pid}"
            
            # Build the response
            response = {
                "citation": citation,
                "url": url,
                "format": config.format,
                "details": {
                    "title": title,
                    "release_date": release_date,
                    "product_id": config.pid
                }
            }
            
            return RenderableResponse(
                content=json.dumps(response, indent=2),
                media_type="application/json"
            )
        except Exception as e:
            logger.error(f"Error in get_citation tool: {e}")
            return RenderableResponse(
                content=f"Error generating citation: {str(e)}",
                media_type="text/plain"
            )
        finally:
            await client.close()


class TrackFigureConfig(BaseModel):
    """Configuration for the track_figure tool."""
    
    pid: str = Field(..., description="StatCan Product ID (PID)")
    figure_name: str = Field(..., description="Name or number of the figure")
    figure_description: str = Field("", description="Description of the figure")
    vector_ids: list[str] = Field([], description="Vector IDs used in the figure")

class TrackFigureTool(BaseTool[TrackFigureConfig]):
    """Tool for tracking and referencing figures from StatCan data."""
    
    name = "track_figure"
    description = "Track and reference a figure created from Statistics Canada data"
    config_model = TrackFigureConfig
    
    async def execute(self, config: TrackFigureConfig) -> RenderableResponse:
        """Execute the track_figure tool."""
        client = WDSClient()
        
        try:
            # Get the metadata for this product ID
            metadata = await client.get_cube_metadata(config.pid)
            
            if metadata.get("status") \!= "SUCCESS":
                return RenderableResponse(
                    content=f"Error retrieving metadata for PID {config.pid}: {metadata.get('object', 'Unknown error')}",
                    media_type="text/plain"
                )
            
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
                "figure_name": config.figure_name,
                "description": config.figure_description or f"Figure based on {title}",
                "source_dataset": {
                    "title": title,
                    "pid": config.pid,
                    "release_date": release_date,
                    "url": f"https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid={config.pid}"
                },
                "vectors": config.vector_ids,
                "citation": f"Source: Statistics Canada, {title} (Table {config.pid}), {release_date}."
            }
            
            # Create a user-friendly note about the figure
            note = f"""
Figure {config.figure_name} is based on Statistics Canada data from "{title}" (Table {config.pid}).
Source: Statistics Canada, Table {config.pid}, {release_date}.
URL: https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid={config.pid}
            """.strip()
            
            # Combine into final response
            response = {
                "figure_reference": figure_reference,
                "note": note
            }
            
            return RenderableResponse(
                content=json.dumps(response, indent=2),
                media_type="application/json"
            )
        except Exception as e:
            logger.error(f"Error in track_figure tool: {e}")
            return RenderableResponse(
                content=f"Error tracking figure: {str(e)}",
                media_type="text/plain"
            )
        finally:
            await client.close()

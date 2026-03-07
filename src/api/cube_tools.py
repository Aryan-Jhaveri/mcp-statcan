import httpx
import datetime
import time
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel

from ..util.registry import ToolRegistry
# Import necessary models
from ..models.api_models import (
    ProductIdInput,
    CubeMetadataInput,
    CubeListInput,
    CubeSearchInput,
    FullTableDownloadCSVInput,
    FullTableDownloadSDMXInput,
    CubeCoordInput,
    CubeCoordLatestNInput,
    BulkCubeCoordInput,
    DEFAULT_TRUNCATION_LIMIT,
)
# Import coordinate padding utility
from ..util.coordinate import pad_coordinate
# Import BASE_URL and timeouts from config
from ..config import BASE_URL, TIMEOUT_MEDIUM, TIMEOUT_LARGE
from ..util.logger import log_ssl_warning, log_search_progress, log_data_validation_warning, log_server_debug
from ..util.cache import get_cached_cubes_list_lite, get_cache_stats
from ..util.truncation import truncate_response, truncate_with_guidance, summarize_cube_metadata

def register_cube_tools(registry: ToolRegistry):
    """Register all cube-related API tools with the MCP server."""

    async def _fetch_all_cubes_list_lite_raw() -> List[Dict[str, Any]]:
        """Raw API fetch for cache use — returns full unpaginated list."""
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT_LARGE, verify=False) as client:
            response = await client.get("/getAllCubesListLite")
            response.raise_for_status()
            return response.json()




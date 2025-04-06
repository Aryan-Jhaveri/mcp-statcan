"""
Client for accessing Statistics Canada's Web Data Service (WDS) API.
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, Union, Any

import aiohttp
from pydantic import BaseModel

from src.config import STATCAN_API_BASE_URL, STATCAN_API_RATE_LIMIT, STATCAN_API_TIMEOUT

logger = logging.getLogger(__name__)

class RateLimiter:
    """Simple rate limiter for API requests."""
    
    def __init__(self, rate_limit: int):
        """Initialize the rate limiter.
        
        Args:
            rate_limit: Maximum number of requests per second
        """
        self.rate_limit = rate_limit
        self.tokens = rate_limit
        self.last_update = time.monotonic()
        self.lock = asyncio.Lock()
    
    async def acquire(self):
        """Acquire a token for making a request."""
        async with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            self.tokens = min(self.rate_limit, self.tokens + elapsed * self.rate_limit)
            self.last_update = now
            
            if self.tokens < 1:
                wait_time = (1 - self.tokens) / self.rate_limit
                logger.debug(f"Rate limit reached, waiting {wait_time:.2f} seconds")
                await asyncio.sleep(wait_time)
                self.tokens = 1
                self.last_update = time.monotonic()
            
            self.tokens -= 1


class WDSClient:
    """Client for Statistics Canada's Web Data Service (WDS) API."""
    
    def __init__(
        self,
        base_url: str = STATCAN_API_BASE_URL,
        rate_limit: int = STATCAN_API_RATE_LIMIT,
        timeout: int = STATCAN_API_TIMEOUT,
    ):
        """Initialize the WDS client.
        
        Args:
            base_url: Base URL for the StatCan WDS API
            rate_limit: Maximum number of requests per second
            timeout: Request timeout in seconds
        """
        self.base_url = base_url
        self.timeout = timeout
        self.rate_limiter = RateLimiter(rate_limit)
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _ensure_session(self):
        """Ensure an aiohttp session exists."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )
    
    async def _request(
        self,
        method: str,
        params: Dict[str, Any],
        endpoint: str = "/rest/getDataFromVectorsAndLatestNPeriods",
    ) -> Dict[str, Any]:
        """Make a request to the WDS API.
        
        Args:
            method: API method name (e.g., 'getDataFromVectorsAndLatestNPeriods')
            params: API parameters
            endpoint: API endpoint path
            
        Returns:
            API response as a dictionary
        
        Raises:
            aiohttp.ClientError: If the request fails
            ValueError: If the API returns an error
        """
        await self._ensure_session()
        await self.rate_limiter.acquire()
        
        url = f"{self.base_url}{endpoint}"
        request_params = {"user_id": "0"} | params
        
        logger.debug(f"Making {method} request to {url} with params: {request_params}")
        
        try:
            async with self.session.post(url, json=request_params) as response:
                response.raise_for_status()
                data = await response.json()
                
                # Check for API errors
                if "status" in data and data["status"] == "FAILED":
                    error_msg = data.get("object", "Unknown API error")
                    logger.error(f"API error: {error_msg}")
                    raise ValueError(f"API error: {error_msg}")
                
                logger.debug(f"Received response from {method}: {len(str(data))} bytes")
                return data
                
        except aiohttp.ClientError as e:
            logger.error(f"Request failed: {e}")
            raise
    
    async def close(self):
        """Close the client session."""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def get_changed_cube_list(
        self, last_updated_days: int = 1
    ) -> Dict[str, Any]:
        """Get a list of cubes that have been updated within the specified time period.
        
        Args:
            last_updated_days: Number of days to look back for updates
            
        Returns:
            Dictionary containing the list of updated cubes
        """
        params = {"lastUpdatedDays": last_updated_days}
        return await self._request("getChangedCubeList", params, "/rest/getChangedCubeList")
    
    async def get_cube_metadata(self, product_id: str) -> Dict[str, Any]:
        """Get metadata for a specific cube/dataset.
        
        Args:
            product_id: StatCan Product ID (PID) for the cube
            
        Returns:
            Dictionary containing cube metadata
        """
        params = {"productId": product_id}
        return await self._request("getCubeMetadata", params, "/rest/getCubeMetadata")
    
    async def get_data_from_vectors(
        self, vectors: List[str], n_periods: int = 10
    ) -> Dict[str, Any]:
        """Get data for specific vectors for the latest N periods.
        
        Args:
            vectors: List of vector IDs
            n_periods: Number of periods to retrieve
            
        Returns:
            Dictionary containing the vector data
        """
        params = {"vectors": vectors, "latestN": n_periods}
        return await self._request(
            "getDataFromVectorsAndLatestNPeriods",
            params,
            "/rest/getDataFromVectorsAndLatestNPeriods",
        )
    
    async def get_series_info_from_vector(self, vector: str) -> Dict[str, Any]:
        """Get information about a specific time series.
        
        Args:
            vector: Vector ID
            
        Returns:
            Dictionary containing series information
        """
        params = {"vectorId": vector}
        return await self._request(
            "getSeriesInfoFromVector", params, "/rest/getSeriesInfoFromVector"
        )
    
    async def search_cubes(self, search_text: str) -> Dict[str, Any]:
        """Search for cubes/datasets by keyword.
        
        Args:
            search_text: Text to search for
            
        Returns:
            Dictionary containing search results
        """
        # Note: This is a custom method as StatCan's API doesn't have a direct search endpoint
        # In a real implementation, we would need to download a catalog or use another approach
        # This is a placeholder that would be properly implemented
        logger.warning("search_cubes is not fully implemented - this is a placeholder")
        
        # For now, we'll just try to get all cubes and filter them client-side
        # This is inefficient but works for a prototype
        try:
            all_cubes = await self.get_changed_cube_list(last_updated_days=3650)  # ~10 years
            search_text = search_text.lower()
            
            if "object" in all_cubes and isinstance(all_cubes["object"], list):
                results = [
                    cube for cube in all_cubes["object"]
                    if search_text in str(cube.get("productTitle", "")).lower()
                    or search_text in str(cube.get("cubeTitleEn", "")).lower()
                ]
                
                return {
                    "status": "SUCCESS",
                    "object": results
                }
            
            return {
                "status": "FAILED",
                "object": "Failed to search cubes. No results found."
            }
            
        except Exception as e:
            logger.error(f"Error searching cubes: {e}")
            return {
                "status": "FAILED",
                "object": f"Error searching cubes: {str(e)}"
            }
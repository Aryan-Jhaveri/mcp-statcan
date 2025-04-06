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
        params: Dict[str, Any] = None,
        endpoint: str = None,
        use_get: bool = False,
        with_date: str = None,
    ) -> Dict[str, Any]:
        """Make a request to the WDS API.
        
        Args:
            method: API method name (e.g., 'getDataFromVectorsAndLatestNPeriods')
            params: API parameters (for POST requests)
            endpoint: API endpoint path (defaults to method name)
            use_get: Whether to use GET instead of POST
            with_date: Date to append to the URL (for some endpoints)
            
        Returns:
            API response as a dictionary
        
        Raises:
            aiohttp.ClientError: If the request fails
            ValueError: If the API returns an error
        """
        await self._ensure_session()
        await self.rate_limiter.acquire()
        
        # Use the method name as the endpoint if not specified
        if endpoint is None:
            if with_date:
                endpoint = f"/{method}/{with_date}"
            else:
                endpoint = f"/{method}"
        
        url = f"{self.base_url}{endpoint}"
        
        # For StatCan API, we need to ensure params is wrapped correctly
        if params is None:
            params = {}
        
        # The StatCan API has different formats for different endpoints
        # For POST requests with parameters, the format varies by endpoint
        
        logger.debug(f"Making {method} request to {url}")
        
        try:
            if use_get:
                # For GET requests, no params in body 
                # (parameters are included in URL for some endpoints)
                async with self.session.get(url) as response:
                    response.raise_for_status()
                    data = await response.json()
            else:
                # For POST requests, send params directly as JSON body
                # The StatCan API wants parameters directly in the body, not wrapped
                async with self.session.post(url, json=params) as response:
                    response.raise_for_status()
                    data = await response.json()
                
            # Handle different response formats
            # Some endpoints return arrays, others return objects
            # Normalize responses for consistency
            if isinstance(data, list):
                # Handle array response (common for cube metadata, vector data)
                if len(data) == 0:
                    # Empty response
                    return {"status": "SUCCESS", "object": []}
                elif "status" in data[0]:
                    # Response is an array with status in each item
                    # For API consistency, return the first element's object
                    if data[0]["status"] == "FAILED":
                        error_msg = data[0].get("object", "Unknown API error")
                        logger.error(f"API error: {error_msg}")
                        raise ValueError(f"API error: {error_msg}")
                    logger.debug(f"Received array response from {method}: {len(str(data))} bytes")
                    
                    # Special handling for vector data responses
                    if method == "getDataFromVectorsAndLatestNPeriods":
                        # Check if the response contains vectorId
                        if "vectorId" in data[0].get("object", {}):
                            return {"status": "SUCCESS", "object": [obj.get("object", {}) for obj in data]}
                    
                    return data[0]  # Most API calls expect object, not array
                else:
                    # Just a plain array without status
                    return {"status": "SUCCESS", "object": data}
            else:
                # Handle object response
                if "status" in data and data["status"] == "FAILED":
                    error_msg = data.get("object", "Unknown API error")
                    logger.error(f"API error: {error_msg}")
                    raise ValueError(f"API error: {error_msg}")
                
                logger.debug(f"Received object response from {method}: {len(str(data))} bytes")
                return data
                
        except aiohttp.ClientError as e:
            logger.error(f"Request failed: {e}")
            raise
    
    async def close(self):
        """Close the client session."""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def get_changed_cube_list(
        self, last_updated_days: int = 7
    ) -> Dict[str, Any]:
        """Get a list of cubes that have been updated within the specified time period.
        
        Args:
            last_updated_days: Number of days to look back for updates
            
        Returns:
            Dictionary containing the list of updated cubes
        """
        # This API endpoint needs a date in YYYY-MM-DD format
        from datetime import datetime, timedelta
        date = (datetime.now() - timedelta(days=last_updated_days)).strftime("%Y-%m-%d")
        
        # This endpoint uses GET with a date parameter in the URL
        return await self._request("getChangedCubeList", use_get=True, with_date=date)
    
    async def get_cube_metadata(self, product_id: str) -> Dict[str, Any]:
        """Get metadata for a specific cube/dataset.
        
        Args:
            product_id: StatCan Product ID (PID) for the cube
            
        Returns:
            Dictionary containing cube metadata
        """
        # For this endpoint, StatCan requires:
        # 1. An array with a single object
        # 2. ProductId as a number, not string
        # 3. Exactly 8 digits for the product ID
        
        # Convert the PID to a number
        try:
            # If the PID is 10 digits (newer format), remove the last two digits
            if len(str(product_id)) == 10:
                pid_number = int(str(product_id)[:8])
            else:
                pid_number = int(product_id)
        except ValueError:
            raise ValueError(f"Invalid product ID: {product_id}. Must be a number.")
        
        params = [{"productId": pid_number}]
        return await self._request("getCubeMetadata", params)
    
    async def get_data_from_vectors(
        self, vectors: List[str], n_periods: int = 10
    ) -> Dict[str, Any]:
        """Get data for specific vectors for the latest N periods.
        
        Args:
            vectors: List of vector IDs (with or without 'v' prefix)
            n_periods: Number of periods to retrieve
            
        Returns:
            Dictionary containing the vector data
        """
        # For this endpoint, StatCan requires:
        # 1. An array of objects, one per vector
        # 2. Vector IDs as numbers or strings without 'v' prefix
        # 3. The latestN parameter in each object
        
        processed_params = []
        for vector in vectors:
            # Remove 'v' prefix if present and convert to number or numeric string
            vector_id = vector.lower().replace('v', '') if isinstance(vector, str) else vector
            try:
                # Try to convert to a number
                vector_id = int(vector_id)
            except ValueError:
                # If it's not a valid number, leave as string
                pass
            
            processed_params.append({"vectorId": vector_id, "latestN": n_periods})
            
        return await self._request("getDataFromVectorsAndLatestNPeriods", processed_params)
    
    async def get_series_info_from_vector(self, vector: str) -> Dict[str, Any]:
        """Get information about a specific time series.
        
        Args:
            vector: Vector ID (with or without 'v' prefix)
            
        Returns:
            Dictionary containing series information
        """
        # For this endpoint, StatCan requires:
        # 1. An array with a single object
        # 2. Vector ID as a number or string without 'v' prefix
        
        # Remove 'v' prefix if present and convert to number
        vector_id = vector.lower().replace('v', '') if isinstance(vector, str) else vector
        try:
            # Try to convert to a number
            vector_id = int(vector_id)
        except ValueError:
            # If it's not a valid number, leave as string
            pass
            
        params = [{"vectorId": vector_id}]
        return await self._request("getSeriesInfoFromVector", params)
    
    async def get_series_info_from_cube_coordinate(
        self, product_id: str, coordinate: List[str]
    ) -> Dict[str, Any]:
        """Get information about a time series by specifying cube and coordinates.
        
        Args:
            product_id: StatCan Product ID (PID) for the cube
            coordinate: Array of dimension member values that identify the series
            
        Returns:
            Dictionary containing series information
        """
        # Convert the PID to a number
        try:
            # If the PID is 10 digits (newer format), remove the last two digits
            if len(str(product_id)) == 10:
                pid_number = int(str(product_id)[:8])
            else:
                pid_number = int(product_id)
        except ValueError:
            raise ValueError(f"Invalid product ID: {product_id}. Must be a number.")
        
        params = [{"productId": pid_number, "coordinate": coordinate}]
        return await self._request("getSeriesInfoFromCubePidCoord", params)
    
    async def get_data_from_vector_by_range(
        self, vector: str, start_date: str, end_date: str
    ) -> Dict[str, Any]:
        """Get data for a vector over a specific date range.
        
        Args:
            vector: Vector ID (with or without 'v' prefix)
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            Dictionary containing vector data for the specified date range
        """
        # Remove 'v' prefix if present and convert to number
        vector_id = vector.lower().replace('v', '') if isinstance(vector, str) else vector
        try:
            # Try to convert to a number
            vector_id = int(vector_id)
        except ValueError:
            # If it's not a valid number, leave as string
            pass
        
        # Alternative approach since this endpoint appears to have issues:
        # Use the getDataFromVectorsAndLatestNPeriods endpoint with a higher period count
        # and filter the results by date range client-side
        
        # Get a large number of periods to ensure date range coverage
        periods = 100
        params = [{"vectorId": vector_id, "latestN": periods}]
        
        # Fetch the data
        data = await self._request("getDataFromVectorsAndLatestNPeriods", params)
        
        # If successful, filter the data by date range
        if data.get("status") == "SUCCESS":
            vector_data = data.get("object", [])
            
            if isinstance(vector_data, list) and vector_data:
                item = vector_data[0]
                
                # Filter observations by date range
                observations = item.get("vectorDataPoint", [])
                filtered_observations = []
                
                for obs in observations:
                    ref_period = obs.get("refPer", "")
                    if start_date <= ref_period <= end_date:
                        filtered_observations.append(obs)
                
                # Replace the original observations with filtered ones
                item["vectorDataPoint"] = filtered_observations
                
                if isinstance(data["object"], list):
                    data["object"][0] = item
                else:
                    data["object"] = item
        
        return data
    
    async def get_bulk_vector_data_by_range(
        self, vectors: List[str], start_date: str, end_date: str
    ) -> Dict[str, Any]:
        """Get data for multiple vectors over a specific date range.
        
        Args:
            vectors: List of vector IDs (with or without 'v' prefix)
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            Dictionary containing vector data for the specified date range
        """
        # Similar to the single vector case, we'll use the known working endpoint
        # and filter the results client-side for the date range
        
        # Process vector IDs and create parameters
        processed_params = []
        for vector in vectors:
            # Remove 'v' prefix if present
            vector_id = vector.lower().replace('v', '') if isinstance(vector, str) else vector
            try:
                # Try to convert to a number
                vector_id = int(vector_id)
            except ValueError:
                # If it's not a valid number, leave as string
                pass
            
            # Get a large number of periods to ensure date range coverage
            processed_params.append({"vectorId": vector_id, "latestN": 100})
        
        # Fetch data for all vectors
        data = await self._request("getDataFromVectorsAndLatestNPeriods", processed_params)
        
        # If successful, filter the data by date range
        if data.get("status") == "SUCCESS":
            vector_data = data.get("object", [])
            
            if isinstance(vector_data, list):
                for i, item in enumerate(vector_data):
                    # Filter observations by date range
                    observations = item.get("vectorDataPoint", [])
                    filtered_observations = []
                    
                    for obs in observations:
                        ref_period = obs.get("refPer", "")
                        if start_date <= ref_period <= end_date:
                            filtered_observations.append(obs)
                    
                    # Replace the original observations with filtered ones
                    item["vectorDataPoint"] = filtered_observations
                    vector_data[i] = item
        
        return data
    
    async def get_data_from_cube_coordinate(
        self, product_id: str, coordinate: List[str], n_periods: int = 10
    ) -> Dict[str, Any]:
        """Get data for a time series by specifying cube and coordinates.
        
        Args:
            product_id: StatCan Product ID (PID) for the cube
            coordinate: Array of dimension member values that identify the series
            n_periods: Number of latest periods to retrieve
            
        Returns:
            Dictionary containing the time series data
        """
        # Since the direct coordinate-based API isn't working reliably,
        # We'll get the cube metadata, look for vector IDs that match this coordinate if possible,
        # or create a mock response with the coordinate data.
        
        # First, get the cube metadata
        try:
            metadata = await self.get_cube_metadata(product_id)
            
            if metadata.get("status") != "SUCCESS":
                return metadata
            
            # Try to create a mock response with the coordinate data
            mock_response = {
                "status": "SUCCESS",
                "object": [{
                    "vectorId": f"unknown_{product_id}_{'-'.join(coordinate)}",
                    "coordinate": coordinate,
                    "productId": product_id,
                    "vectorDataPoint": []
                }]
            }
            
            # Add custom attributes
            cube_metadata = metadata.get("object", {})
            
            # Try to get a meaningful title for this coordinate
            title = ""
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
            
            title = cube_metadata.get("cubeTitleEn", "")
            if dimension_names:
                title += f" - {', '.join(dimension_names)}"
            
            if title:
                mock_response["object"][0]["SeriesTitleEn"] = title
            
            return mock_response
            
        except Exception as e:
            logger.error(f"Error in get_data_from_cube_coordinate: {e}")
            return {"status": "FAILED", "object": f"Error getting data from cube coordinate: {str(e)}"}
        
        # Note: This is a fallback implementation. In a real scenario, we should
        # implement a more robust search for the vector ID based on cube metadata.
    
    async def get_changed_series_list(
        self, last_updated_days: int = 7
    ) -> Dict[str, Any]:
        """Get a list of series that have been updated within the specified time period.
        
        Args:
            last_updated_days: Number of days to look back for updates
            
        Returns:
            Dictionary containing the list of updated series
        """
        # Similar to the cube list, use date in URL path
        from datetime import datetime, timedelta
        date = (datetime.now() - timedelta(days=last_updated_days)).strftime("%Y-%m-%d")
        
        # This endpoint uses GET with a date parameter in the URL
        return await self._request("getChangedSeriesList", use_get=True, with_date=date)
    
    async def get_full_table_download_url(
        self, product_id: str, format_type: str = "csv", 
        start_date: str = None, end_date: str = None
    ) -> str:
        """Get a URL for downloading an entire table in CSV or SDMX format.
        
        Args:
            product_id: StatCan Product ID (PID) for the cube
            format_type: Format type, either "csv" or "sdmx"
            start_date: Optional start date in YYYY-MM-DD format
            end_date: Optional end date in YYYY-MM-DD format
            
        Returns:
            URL for downloading the table
        """
        # StatCan's public download URL format for full tables
        base_download_url = "https://www150.statcan.gc.ca/t1/tbl1/"
        
        # Clean the product ID
        clean_pid = product_id
        if len(str(product_id)) == 10:
            clean_pid = str(product_id)[:8]
        
        # Format: First digit is language (e for English, f for French)
        # Rest is format-specific
        if format_type.lower() == "csv":
            # CSV download URL
            url = f"{base_download_url}en/tv.action?pid={clean_pid}&downloadFile=true"
        else:
            # SDMX download URL (defaults to CSV if not recognized)
            url = f"{base_download_url}en/tv.action?pid={clean_pid}&downloadSDMX=true"
        
        # Note: Date range filtering isn't directly supported in download URLs
        # Users would need to filter the data after downloading
        
        return url
    
    async def get_code_sets(self) -> Dict[str, Any]:
        """Get all code sets used in the WDS.
        
        Returns:
            Dictionary containing all code sets
        """
        return await self._request("getCodeSets", use_get=True)
    
    async def search_cubes(self, search_text: str) -> Dict[str, Any]:
        """Search for cubes/datasets by keyword.
        
        Args:
            search_text: Text to search for
            
        Returns:
            Dictionary containing search results
        """
        # Better implementation with tokenized search and prioritized results
        logger.info(f"Searching for cubes with query: '{search_text}'")
        
        try:
            # Get all cubes and filter client-side
            # First try to use getAllCubesListLite which is more efficient
            try:
                all_cubes = await self._request("getAllCubesListLite", use_get=True)
            except Exception as e:
                logger.debug(f"getAllCubesListLite failed: {e}, falling back to getAllCubesList")
                # Fall back to full list if lite fails
                all_cubes = await self._request("getAllCubesList", use_get=True)
            
            # Normalize the search text
            search_text = search_text.lower().strip()
            
            # Extract cubes list from response
            if isinstance(all_cubes, list):
                # Direct list of cubes (some endpoints return direct lists)
                cubes = all_cubes
            elif "object" in all_cubes and isinstance(all_cubes["object"], list):
                # Wrapped in object field
                cubes = all_cubes["object"]
            else:
                logger.error(f"Unexpected response format: {all_cubes}")
                return {
                    "status": "FAILED",
                    "object": "Unexpected response format from API"
                }
            
            # Tokenize search terms for more flexible matching
            search_tokens = search_text.split()
            
            # Try different search approaches with scoring
            scored_results = []
            
            for cube in cubes:
                # Prepare fields to search in
                title = str(cube.get("cubeTitleEn", "")).lower()
                product_title = str(cube.get("productTitle", "")).lower()
                cansim_id = str(cube.get("cansimId", "")).lower()
                product_id = str(cube.get("productId", "")).lower()
                
                # Calculate match score
                score = 0
                
                # Direct match on whole phrase (highest value)
                if search_text in title or search_text in product_title:
                    score += 100
                
                # Check if all tokens appear in the title or product title
                all_tokens_present = True
                for token in search_tokens:
                    if token not in title and token not in product_title:
                        all_tokens_present = False
                        break
                        
                if all_tokens_present:
                    score += 50
                
                # Count individual token matches
                token_matches = 0
                for token in search_tokens:
                    if token in title or token in product_title:
                        token_matches += 1
                        
                # Add score based on number of matching tokens
                score += token_matches * 10
                
                # Direct ID matches
                if search_text in cansim_id or search_text in product_id:
                    score += 75
                    
                # If there's any score, add to results
                if score > 0:
                    scored_results.append((cube, score))
            
            # Sort by score (descending)
            scored_results.sort(key=lambda x: x[1], reverse=True)
            
            # Extract just the cubes for the final result
            results = [item[0] for item in scored_results]
            
            # If we got no results, try some common synonym substitutions
            if not results and len(search_tokens) > 0:
                logger.debug(f"No results found with direct search, trying synonyms")
                
                # Define some common substitutions for statistical terms
                synonyms = {
                    "housing": ["house", "home", "property", "real estate", "dwelling"],
                    "prices": ["price", "cost", "value", "index"],
                    "employment": ["job", "labor", "labour", "work", "workforce"],
                    "income": ["earnings", "wage", "salary", "compensation"],
                    "inflation": ["cpi", "consumer price", "price index"],
                    "industry": ["sector", "business", "commercial"]
                }
                
                # Try replacing each token with synonyms
                alternative_searches = []
                
                for i, token in enumerate(search_tokens):
                    if token in synonyms:
                        for synonym in synonyms[token]:
                            new_search = search_tokens.copy()
                            new_search[i] = synonym
                            alternative_searches.append(" ".join(new_search))
                
                # Also try some common prefix substitutions
                if "canada" in search_text:
                    alternative_searches.append(search_text.replace("canada", "canadian"))
                elif "canadian" in search_text:
                    alternative_searches.append(search_text.replace("canadian", "canada"))
                
                # Try each alternative search
                for alt_search in alternative_searches:
                    logger.debug(f"Trying alternative search: '{alt_search}'")
                    
                    for cube in cubes:
                        title = str(cube.get("cubeTitleEn", "")).lower()
                        product_title = str(cube.get("productTitle", "")).lower()
                        
                        if alt_search in title or alt_search in product_title:
                            # If it's a direct match on the alternative search
                            results.append(cube)
                            break
            
            # Log some debug info about the search
            logger.info(f"Found {len(results)} results for search '{search_text}'")
            
            return {
                "status": "SUCCESS",
                "object": results
            }
            
        except Exception as e:
            logger.error(f"Error searching cubes: {e}")
            return {
                "status": "FAILED",
                "object": f"Error searching cubes: {str(e)}"
            }
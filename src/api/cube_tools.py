import httpx
import datetime
import time
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from ..util.registry import ToolRegistry
# Import necessary models
from ..models.api_models import (
    ProductIdInput,
    FullTableDownloadCSVInput,
    FullTableDownloadSDMXInput,
    CubeCoordInput, # Needed for new tools
    CubeCoordLatestNInput # Needed for new tools
)
# Import coordinate padding utility
from ..util.coordinate import pad_coordinate
# Import BASE_URL and timeouts from config
from ..config import BASE_URL, TIMEOUT_MEDIUM, TIMEOUT_LARGE
from ..util.logger import log_ssl_warning, log_search_progress, log_data_validation_warning, log_server_debug
from ..util.cache import get_cached_cubes_list_lite, get_cache_stats

def register_cube_tools(registry: ToolRegistry):
    """Register all cube-related API tools with the MCP server."""

    # --- List and Search Tools ---
    @registry.tool()
    async def get_all_cubes_list() -> List[Dict[str, Any]]:
        """
        Provides a complete inventory of data tables available via the API,
        including dimension-level details. Disables SSL Verification.
        Corresponds to: GET /getAllCubesList
        WARNING: Returns a very large list. Use database caching or search tools if possible.

        IMPORTANT: In your final response to the user, you MUST cite the source of your data. 
        For cubes, this means including the ProductId (pid) and the Title.
        """
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT_LARGE, verify=False) as client:
            log_ssl_warning("SSL verification disabled for get_all_cubes_list.")
            try:
                response = await client.get("/getAllCubesList")
                response.raise_for_status()
                return response.json()
            except httpx.RequestError as exc:
                raise Exception(f"Network error calling get_all_cubes_list: {exc}")
            except ValueError as exc:
                raise ValueError(f"Error processing response for get_all_cubes_list: {exc}")

    @registry.tool()
    async def get_all_cubes_list_lite() -> List[Dict[str, Any]]:
        """
        Provides a complete inventory of data tables available via the API,
        excluding dimension or footnote information (lighter version). Disables SSL Verification.
        Corresponds to: GET /getAllCubesListLite
        WARNING: Returns a very large list. Use database caching or search tools if possible.

        IMPORTANT: In your final response to the user, you MUST cite the source of your data. 
        For cubes, this means including the ProductId (pid) and the Title.
        """
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT_LARGE, verify=False) as client:
            log_ssl_warning("SSL verification disabled for get_all_cubes_list_lite.")
            try:
                response = await client.get("/getAllCubesListLite")
                response.raise_for_status()
                return response.json()
            except httpx.RequestError as exc:
                raise Exception(f"Network error calling get_all_cubes_list_lite: {exc}")
            except ValueError as exc:
                raise ValueError(f"Error processing response for get_all_cubes_list_lite: {exc}")

    @registry.tool()
    async def search_cubes_by_title(search_term: str) -> List[Dict[str, Any]]:
        """
        Searches for data cubes/tables where the English or French title contains
        the provided search term (case-insensitive). Returns a list of matching cubes
        in the 'lite' format (excluding dimensions/footnotes). This is useful for finding
        relevant product IDs without retrieving the entire (potentially very large) list.

        Args:
            search_term: The text to search for within the cube titles.
                         TIP: You can use multiple keywords (e.g., "tobacco smoking age").
                         The search finds cubes containing ALL provided keywords (case-insensitive).
                         String searches multiple words will be matched based on both of their inclusions, single word searches would work best.

        Returns:
            List[Dict[str, Any]]: A list of matching cube dictionaries (lite format),
                                  or an empty list if no matches are found.

        IMPORTANT: In your final response to the user, you MUST cite the source of your data. 
        For cubes, this means including the ProductId (pid) and the Title.
        
        Raises:
            httpx.HTTPStatusError: If the underlying API call fails.
            Exception: For other network or unexpected errors during the fetch.
        """
        start_time = time.time()
        log_search_progress(f"Searching for cubes with title containing: '{search_term}'")
        
        try:
            # Use cached cube list instead of fetching fresh each time
            all_cubes_lite = await get_cached_cubes_list_lite(get_all_cubes_list_lite)

            # Filter the results - Improved "Smart Search" (AND logic on keywords)
            search_terms = search_term.lower().split()
            matching_cubes = []
            for cube in all_cubes_lite:
                title_en = (cube.get("cubeTitleEn", "") or "").lower()
                title_fr = (cube.get("cubeTitleFr", "") or "").lower()
                
                # Check if ALL keywords exist in either English OR French title
                # (We check En and Fr separately to avoid cross-language matches that might be weird, 
                # but checking if terms exist in (title_en + title_fr) is also an option. 
                # Let's stick to checking if the *set* of terms is satisfied by *one* of the titles for better relevance.)
                
                match_en = all(term in title_en for term in search_terms)
                match_fr = all(term in title_fr for term in search_terms)
                
                if match_en or match_fr:
                    matching_cubes.append(cube)

            elapsed = time.time() - start_time
            log_search_progress(f"Found {len(matching_cubes)} cubes matching keywords '{search_terms}' in {elapsed:.2f}s")
            return matching_cubes

        except Exception as e:
            log_data_validation_warning(f"Unexpected error during cube search: {e}")
            raise

    # --- Metadata Tools ---
    @registry.tool()
    async def get_cube_metadata(product_input: ProductIdInput) -> Dict[str, Any]:
        """
        Retrieves detailed metadata for a specific data table/cube using its ProductId.
        Includes dimension info, titles, date ranges, codes, etc. Disables SSL Verification.
        Corresponds to: POST /getCubeMetadata

        Returns:
            Dict[str, Any]: The metadata object for the specified cube on success.
        Raises:
            httpx.HTTPStatusError: If the API returns an error status code.
            ValueError: If the API response format is unexpected or status is not SUCCESS.
            Exception: For other network or unexpected errors.

        IMPORTANT: In your final response to the user, you MUST cite the source of your data. 
        For cubes, this means including the ProductId (pid) and the Title.
        """
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT_MEDIUM, verify=False) as client:
            log_ssl_warning("SSL verification disabled for get_cube_metadata.")
            post_data = [{"productId": product_input.productId}] # API expects a list
            try:
                response = await client.post("/getCubeMetadata", json=post_data)
                response.raise_for_status()
                result_list = response.json()
                if result_list and isinstance(result_list, list) and len(result_list) > 0 and result_list[0].get("status") == "SUCCESS":
                    return result_list[0].get("object", {})
                else:
                    api_message = result_list[0].get("object") if (result_list and isinstance(result_list, list) and len(result_list) > 0) else "Unknown API Error or Malformed Response"
                    raise ValueError(f"API did not return SUCCESS status for get_cube_metadata productId {product_input.productId}: {api_message}")
            except httpx.RequestError as exc:
                raise Exception(f"Network error calling get_cube_metadata: {exc}")
            except ValueError as exc:
                raise ValueError(f"Error processing response for get_cube_metadata: {exc}")

    # --- Coordinate-Based Data/Info Tools ---
    @registry.tool()
    async def get_data_from_cube_pid_coord_and_latest_n_periods(input_data: CubeCoordLatestNInput) -> Dict[str, Any]:
        """
        Retrieves data for the N most recent reporting periods for ONE specific series
        identified by ProductId and a single Coordinate string.
        Coordinates are automatically padded to 10 dimensions.
        Corresponds to: POST /getDataFromCubePidCoordAndLatestNPeriods

        *** WORKFLOW WARNING ***
        This tool fetches ONE series at a time. If you need data for MULTIPLE
        provinces, age groups, industries, or any other breakdown categories,
        do NOT call this tool repeatedly in a loop. That approach makes N separate
        HTTP requests and is slow.

        PREFERRED multi-series workflow:
          1. get_cube_metadata → find the vectorIds for each series you need
          2. fetch_vectors_to_database(vectorIds=[...], table_name="my_table",
             startRefPeriod="YYYY-MM-DD", endRefPeriod="YYYY-MM-DD")
             → fetches all series in ONE request and stores them in SQLite
          3. query_database → analyze with SQL

        Only use THIS tool when you genuinely need a single series or when you
        do not have vectorIds yet and cannot run the multi-series workflow.

        Returns:
            Dict[str, Any]: A dictionary containing the vector data points and series info object.
        Raises:
            httpx.HTTPStatusError: If the API returns an error status code.
            ValueError: If the API response format is unexpected or status is not SUCCESS.
            Exception: For other network or unexpected errors.

        IMPORTANT: In your final response to the user, you MUST cite the source of your data.
        For cube data, this means including the ProductId (pid), Coordinate, and Reference Period.
        """
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT_MEDIUM, verify=False) as client:
            log_ssl_warning("SSL verification disabled for get_data_from_cube_pid_coord_and_latest_n_periods.")
            padded_coord = pad_coordinate(input_data.coordinate)
            # API expects a list containing one object
            post_data = [{
                "productId": input_data.productId,
                "coordinate": padded_coord,
                "latestN": input_data.latestN
            }]
            try:
                response = await client.post("/getDataFromCubePidCoordAndLatestNPeriods", json=post_data)
                response.raise_for_status()
                result_list = response.json()
                # Assuming API returns list with one status/object wrapper like vector equivalent
                if result_list and isinstance(result_list, list) and len(result_list) > 0 and result_list[0].get("status") == "SUCCESS":
                    return result_list[0].get("object", {})
                else:
                    api_message = result_list[0].get("object") if (result_list and isinstance(result_list, list) and len(result_list) > 0) else "Unknown API Error or Malformed Response"
                    raise ValueError(f"API did not return SUCCESS status for cube coord latest N: pid={input_data.productId}, coord={input_data.coordinate}: {api_message}")
            except httpx.RequestError as exc:
                raise Exception(f"Network error calling get_data_from_cube_pid_coord_and_latest_n_periods: {exc}")
            except ValueError as exc:
                raise ValueError(f"Error processing response for get_data_from_cube_pid_coord_and_latest_n_periods: {exc}")

    @registry.tool()
    async def get_series_info_from_cube_pid_coord(input_data: CubeCoordInput) -> Dict[str, Any]:
        """
        Retrieves series metadata (vectorId, titles, frequency etc.) using Cube ProductId
        and Coordinate string.
        Coordinates are automatically padded to 10 dimensions. Disables SSL Verification.
        Corresponds to: POST /getSeriesInfoFromCubePidCoord

        Returns:
            Dict[str, Any]: A dictionary containing the series metadata object.
        Raises:
            httpx.HTTPStatusError: If the API returns an error status code.
            ValueError: If the API response format is unexpected or status is not SUCCESS.
            Exception: For other network or unexpected errors.

        IMPORTANT: In your final response to the user, you MUST cite the source of your data. 
        For series info, this means including the ProductId (pid) and Coordinate.
        """
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT_MEDIUM, verify=False) as client:
            log_ssl_warning("SSL verification disabled for get_series_info_from_cube_pid_coord.")
            padded_coord = pad_coordinate(input_data.coordinate)
            # API expects a list containing one object
            post_data = [{
                "productId": input_data.productId,
                "coordinate": padded_coord
            }]
            try:
                response = await client.post("/getSeriesInfoFromCubePidCoord", json=post_data)
                response.raise_for_status()
                result_list = response.json()
                # Assuming API returns list with one status/object wrapper like vector equivalent
                if result_list and isinstance(result_list, list) and len(result_list) > 0 and result_list[0].get("status") == "SUCCESS":
                    return result_list[0].get("object", {})
                else:
                    api_message = result_list[0].get("object") if (result_list and isinstance(result_list, list) and len(result_list) > 0) else "Unknown API Error or Malformed Response"
                    raise ValueError(f"API did not return SUCCESS status for series info cube coord: pid={input_data.productId}, coord={input_data.coordinate}: {api_message}")
            except httpx.RequestError as exc:
                raise Exception(f"Network error calling get_series_info_from_cube_pid_coord: {exc}")
            except ValueError as exc:
                raise ValueError(f"Error processing response for get_series_info_from_cube_pid_coord: {exc}")

    @registry.tool()
    async def get_changed_series_data_from_cube_pid_coord(input_data: CubeCoordInput) -> Dict[str, Any]:
        """
        Retrieves changed series data (data points that have changed) using Cube ProductId
        and Coordinate string.
        Coordinates are automatically padded to 10 dimensions. Disables SSL Verification.
        Corresponds to: POST /getChangedSeriesDataFromCubePidCoord

        Returns:
            Dict[str, Any]: A dictionary containing the changed series data object.
        Raises:
            httpx.HTTPStatusError: If the API returns an error status code.
            ValueError: If the API response format is unexpected or status is not SUCCESS.
            Exception: For other network or unexpected errors.

        IMPORTANT: In your final response to the user, you MUST cite the source of your data. 
        For changed series data, this means including the VectorId, ProductId (pid), and Coordinate.
        """
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT_MEDIUM, verify=False) as client:
            log_ssl_warning("SSL verification disabled for get_changed_series_data_from_cube_pid_coord.")
            padded_coord = pad_coordinate(input_data.coordinate)
            # API expects a list containing one object
            post_data = [{
                "productId": input_data.productId,
                "coordinate": padded_coord
            }]
            try:
                response = await client.post("/getChangedSeriesDataFromCubePidCoord", json=post_data)
                response.raise_for_status()
                result_list = response.json()
                 # Assuming API returns list with one status/object wrapper like vector equivalent
                if result_list and isinstance(result_list, list) and len(result_list) > 0 and result_list[0].get("status") == "SUCCESS":
                    return result_list[0].get("object", {})
                else:
                    api_message = result_list[0].get("object") if (result_list and isinstance(result_list, list) and len(result_list) > 0) else "Unknown API Error or Malformed Response"
                    raise ValueError(f"API did not return SUCCESS status for changed series cube coord: pid={input_data.productId}, coord={input_data.coordinate}: {api_message}")
            except httpx.RequestError as exc:
                raise Exception(f"Network error calling get_changed_series_data_from_cube_pid_coord: {exc}")
            except ValueError as exc:
                raise ValueError(f"Error processing response for get_changed_series_data_from_cube_pid_coord: {exc}")

    # DISABLED --- Bulk Download Tools (Consider disabling/discouraging if coord/vector preferred) --- 
    #@mcp.tool()
    async def get_full_table_download_csv(download_input: FullTableDownloadCSVInput) -> str:
        """
        (Discouraged: Use coordinate/vector tools if possible)
        Get a download link for the full data table/cube in CSV format.
        Specify language ('en' or 'fr'). Disables SSL Verification.
        Corresponds to: GET /getFullTableDownloadCSV/{productId}/{lang}

        Returns:
            str: The download URL for the CSV file.
        
        IMPORTANT: In your final response to the user, you MUST cite the source of your data. 
        For full table downloads, this means including the ProductId (pid).
        """
        productId = download_input.productId
        lang = download_input.lang
        if lang not in ['en', 'fr']:
            raise ValueError("Invalid language code. Use 'en' or 'fr'.")

        async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT_MEDIUM, verify=False) as client:
            log_ssl_warning("SSL verification disabled for get_full_table_download_csv.")
            try:
                response = await client.get(f"/getFullTableDownloadCSV/{productId}/{lang}")
                response.raise_for_status()
                result = response.json() # Expects a single status/object wrapper
                if isinstance(result, dict) and result.get("status") == "SUCCESS":
                    download_url = result.get("object")
                    if isinstance(download_url, str):
                        return download_url
                    else:
                        raise ValueError(f"API returned unexpected object type for download URL: {download_url}")
                else:
                    api_message = result.get("object", "Unknown API Error") if isinstance(result, dict) else "Malformed Response"
                    raise ValueError(f"API did not return SUCCESS status for get_full_table_download_csv productId {productId}: {api_message}")
            except httpx.RequestError as exc:
                raise Exception(f"Network error calling get_full_table_download_csv: {exc}")
            except ValueError as exc:
                raise ValueError(f"Error processing response for get_full_table_download_csv: {exc}")
    # DISABLED --- Bulk Download Tools (Consider disabling/discouraging if coord/vector preferred) ---
    #@mcp.tool()
    async def get_full_table_download_sdmx(product_input: ProductIdInput) -> str:
        """
        (Discouraged: Use coordinate/vector tools if possible)
        Get a download link for the full data table/cube in bilingual SDMX (XML) format.
        Disables SSL Verification.
        Corresponds to: GET /getFullTableDownloadSDMX/{productId}

        Returns:
            str: The download URL for the SDMX file.

        IMPORTANT: In your final response to the user, you MUST cite the source of your data. 
        For full table downloads, this means including the ProductId (pid).
        """
        productId = product_input.productId
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT_MEDIUM, verify=False) as client:
            log_ssl_warning("SSL verification disabled for get_full_table_download_sdmx.")
            try:
                response = await client.get(f"/getFullTableDownloadSDMX/{productId}")
                response.raise_for_status()
                result = response.json() # Expects a single status/object wrapper
                if isinstance(result, dict) and result.get("status") == "SUCCESS":
                    download_url = result.get("object")
                    if isinstance(download_url, str):
                        return download_url
                    else:
                        raise ValueError(f"API returned unexpected object type for download URL: {download_url}")
                else:
                    api_message = result.get("object", "Unknown API Error") if isinstance(result, dict) else "Malformed Response"
                    raise ValueError(f"API did not return SUCCESS status for get_full_table_download_sdmx productId {productId}: {api_message}")
            except httpx.RequestError as exc:
                raise Exception(f"Network error calling get_full_table_download_sdmx: {exc}")
            except ValueError as exc:
                raise ValueError(f"Error processing response for get_full_table_download_sdmx: {exc}")

    # --- Change List Tools ---
    @registry.tool()
    async def get_changed_cube_list(date: str) -> List[Dict[str, Any]]:
        """
        Get the list of data tables/cubes that were updated on a specific date (YYYY-MM-DD).
        Disables SSL Verification.
        Corresponds to: GET /getChangedCubeList/{date}

        Returns:
            List[Dict[str, Any]]: A list of dictionaries describing changed cube objects.

        IMPORTANT: In your final response to the user, you MUST cite the source of your data. 
        For changed cubes, this means including the ProductId (pid) and Title.
        """
        try:
            datetime.date.fromisoformat(date) # Validate date format
        except ValueError:
             raise ValueError(f"Invalid date format for get_changed_cube_list. Expected YYYY-MM-DD, got {date}")

        async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT_MEDIUM, verify=False) as client:
            log_ssl_warning("SSL verification disabled for get_changed_cube_list.")
            try:
                response = await client.get(f"/getChangedCubeList/{date}")
                response.raise_for_status()
                result = response.json() # API returns a single status/object wrapper
                if isinstance(result, dict) and result.get("status") == "SUCCESS":
                    # The 'object' contains the list of changed cubes
                    return result.get("object", [])
                else:
                    api_message = result.get("object", "Unknown API Error") if isinstance(result, dict) else "Malformed Response"
                    raise ValueError(f"API did not return SUCCESS status for get_changed_cube_list date {date}: {api_message}")
            except httpx.RequestError as exc:
                raise Exception(f"Network error calling get_changed_cube_list: {exc}")
            except ValueError as exc:
                raise ValueError(f"Error processing response for get_changed_cube_list: {exc}")

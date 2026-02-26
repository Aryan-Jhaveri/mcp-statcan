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

    # --- List and Search Tools ---
    @registry.tool()
    async def get_all_cubes_list(list_input: CubeListInput) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Provides a complete inventory of data tables available via the API,
        including dimension-level details. Disables SSL Verification.
        Corresponds to: GET /getAllCubesList

        Results are paginated. Default returns first 100 cubes. Use offset/limit
        to page through. Prefer search_cubes_by_title if you know what you're looking for.

        IMPORTANT: In your final response to the user, you MUST cite the source of your data.
        For cubes, this means including the ProductId (pid) and the Title.
        """
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT_LARGE, verify=False) as client:
            log_ssl_warning("SSL verification disabled for get_all_cubes_list.")
            try:
                response = await client.get("/getAllCubesList")
                response.raise_for_status()
                all_cubes = response.json()
                return truncate_response(all_cubes, list_input.offset, list_input.limit)
            except httpx.RequestError as exc:
                raise Exception(f"Network error calling get_all_cubes_list: {exc}")
            except ValueError as exc:
                raise ValueError(f"Error processing response for get_all_cubes_list: {exc}")

    @registry.tool()
    async def get_all_cubes_list_lite(list_input: CubeListInput) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Provides a complete inventory of data tables available via the API,
        excluding dimension or footnote information (lighter version). Disables SSL Verification.
        Corresponds to: GET /getAllCubesListLite

        Results are paginated. Default returns first 100 cubes. Use offset/limit
        to page through. Prefer search_cubes_by_title if you know what you're looking for.

        IMPORTANT: In your final response to the user, you MUST cite the source of your data.
        For cubes, this means including the ProductId (pid) and the Title.
        """
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT_LARGE, verify=False) as client:
            log_ssl_warning("SSL verification disabled for get_all_cubes_list_lite.")
            try:
                response = await client.get("/getAllCubesListLite")
                response.raise_for_status()
                all_cubes = response.json()
                return truncate_response(all_cubes, list_input.offset, list_input.limit)
            except httpx.RequestError as exc:
                raise Exception(f"Network error calling get_all_cubes_list_lite: {exc}")
            except ValueError as exc:
                raise ValueError(f"Error processing response for get_all_cubes_list_lite: {exc}")

    @registry.tool()
    async def search_cubes_by_title(search_input: CubeSearchInput) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Searches for data cubes/tables where the English or French title contains
        the provided search term (case-insensitive). Returns a list of matching cubes
        in the 'lite' format (excluding dimensions/footnotes).

        Multiple keywords use AND logic (e.g., "tobacco smoking age" finds cubes
        containing ALL three words). Results are capped at max_results (default 25).

        IMPORTANT: In your final response to the user, you MUST cite the source of your data.
        For cubes, this means including the ProductId (pid) and the Title.

        Raises:
            httpx.HTTPStatusError: If the underlying API call fails.
            Exception: For other network or unexpected errors during the fetch.
        """
        start_time = time.time()
        search_term = search_input.search_term
        max_results = search_input.max_results
        log_search_progress(f"Searching for cubes with title containing: '{search_term}'")

        try:
            # Use cached cube list instead of fetching fresh each time
            all_cubes_lite = await get_cached_cubes_list_lite(_fetch_all_cubes_list_lite_raw)

            # Filter the results - AND logic on keywords
            search_terms = search_term.lower().split()
            matching_cubes = []
            for cube in all_cubes_lite:
                title_en = (cube.get("cubeTitleEn", "") or "").lower()
                title_fr = (cube.get("cubeTitleFr", "") or "").lower()

                match_en = all(term in title_en for term in search_terms)
                match_fr = all(term in title_fr for term in search_terms)

                if match_en or match_fr:
                    matching_cubes.append(cube)

            elapsed = time.time() - start_time
            total_found = len(matching_cubes)
            log_search_progress(f"Found {total_found} cubes matching keywords '{search_terms}' in {elapsed:.2f}s")

            if total_found > max_results:
                return {
                    "data": matching_cubes[:max_results],
                    "total_matches": total_found,
                    "showing": max_results,
                    "message": f"Showing {max_results} of {total_found} matches. Increase max_results to see more.",
                }
            return matching_cubes

        except Exception as e:
            log_data_validation_warning(f"Unexpected error during cube search: {e}")
            raise

    # --- Metadata Tools ---
    @registry.tool()
    async def get_cube_metadata(metadata_input: CubeMetadataInput) -> Dict[str, Any]:
        """
        Retrieves detailed metadata for a specific data table/cube using its ProductId.
        Includes dimension info, titles, date ranges, codes, etc. Disables SSL Verification.
        Corresponds to: POST /getCubeMetadata

        Start with summary=True (default). The summary caps each dimension's member
        list at 5 entries and shows total counts. Only set summary=False if you need
        specific vectorIds not visible in the summary.
        To browse ALL members without loading them into context, use store_cube_metadata
        instead — it stores full metadata in SQLite and returns only a compact summary.

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
            post_data = [{"productId": metadata_input.productId}] # API expects a list
            try:
                response = await client.post("/getCubeMetadata", json=post_data)
                response.raise_for_status()
                result_list = response.json()
                if result_list and isinstance(result_list, list) and len(result_list) > 0 and result_list[0].get("status") == "SUCCESS":
                    metadata = result_list[0].get("object", {})
                    if metadata_input.summary:
                        return summarize_cube_metadata(metadata)
                    return metadata
                else:
                    api_message = result_list[0].get("object") if (result_list and isinstance(result_list, list) and len(result_list) > 0) else "Unknown API Error or Malformed Response"
                    raise ValueError(f"API did not return SUCCESS status for get_cube_metadata productId {metadata_input.productId}: {api_message}")
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

    # --- Bulk Coordinate Tools ---
    @registry.tool()
    async def get_series_info_from_cube_pid_coord_bulk(input_data: BulkCubeCoordInput) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Batch-fetch series metadata for MULTIPLE {productId, coordinate} pairs in a
        single API call. Returns vectorId, titles, frequency, etc. for each series.

        Use this instead of calling get_series_info_from_cube_pid_coord in a loop.
        Coordinates are automatically padded to 10 dimensions.
        Corresponds to: POST /getSeriesInfoFromCubePidCoord (accepts array)

        NOTE: Response fields like `scalarFactorCode`, `frequencyCode`, and
        `memberUomCode` use StatCan numeric code values. Call get_code_sets()
        to resolve them to human-readable labels (e.g., frequency 6 = "Monthly").

        Returns:
            List[Dict[str, Any]] or Dict: Series metadata objects, paginated if >50 results.
        Raises:
            httpx.HTTPStatusError: If the API returns an error status code.
            ValueError: If no items return SUCCESS.
            Exception: For other network or unexpected errors.

        IMPORTANT: In your final response cite the ProductId and Coordinate for each series.
        """
        if not input_data.items:
            raise ValueError("items list cannot be empty.")

        async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT_MEDIUM, verify=False) as client:
            log_ssl_warning("SSL verification disabled for get_series_info_from_cube_pid_coord_bulk.")
            post_data = [
                {"productId": item.productId, "coordinate": pad_coordinate(item.coordinate)}
                for item in input_data.items
            ]
            try:
                response = await client.post("/getSeriesInfoFromCubePidCoord", json=post_data)
                response.raise_for_status()
                result_list = response.json()

                results = []
                failures = []
                if isinstance(result_list, list):
                    for item in result_list:
                        if isinstance(item, dict) and item.get("status") == "SUCCESS":
                            results.append(item.get("object", {}))
                        else:
                            failures.append(item)
                            log_data_validation_warning(f"Bulk series info partial failure: {item}")
                else:
                    raise ValueError(f"API response was not a list. Response: {result_list}")

                if not results and failures:
                    raise ValueError(f"API did not return SUCCESS for any item. Failures: {failures}")

                offset = input_data.offset or 0
                limit = input_data.limit or DEFAULT_TRUNCATION_LIMIT
                return truncate_with_guidance(
                    results, offset, limit,
                    "Fields like scalarFactorCode, frequencyCode, and memberUomCode use StatCan "
                    "numeric code values. Call get_code_sets() to resolve them to human-readable "
                    "labels (e.g., frequency 6 = 'Monthly', scalar 0 = 'Units')."
                )
            except httpx.RequestError as exc:
                raise Exception(f"Network error calling get_series_info_from_cube_pid_coord_bulk: {exc}")
            except ValueError as exc:
                raise ValueError(f"Error processing response for get_series_info_from_cube_pid_coord_bulk: {exc}")

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

import httpx
import asyncio
import sqlite3
import json
import os
import datetime # Ensure datetime is imported for date validation
from fastmcp import FastMCP
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Tuple

# --- Configuration ---
# Database file will be created in the same directory as the script
DB_FILE = "temp_statcan_data.db"
# Base URL for the Statistics Canada API
BASE_URL = "https://www150.statcan.gc.ca/t1/wds/rest"
# Number of expected dimension slots for coordinates
EXPECTED_COORD_DIMENSIONS = 10

# --- MCP Server Setup ---
mcp = FastMCP(name="StatCanAPI_DB_Server")

# --- Helper Functions ---
def get_db_connection() -> sqlite3.Connection:
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DB_FILE)
    # Return rows as dictionary-like objects
    conn.row_factory = sqlite3.Row
    return conn

def _infer_sql_type(value: Any) -> str:
    """Infers a basic SQLite data type from a Python value."""
    if isinstance(value, int):
        return "INTEGER"
    elif isinstance(value, float):
        return "REAL"
    elif isinstance(value, (str, bytes, bool, type(None))): # Treat bool/None as TEXT for simplicity
        return "TEXT"
    else:
        # Store complex types like lists/dicts as JSON strings
        return "TEXT"

def _pad_coordinate(coord_str: str) -> str:
    """Pads a coordinate string with '.0' up to EXPECTED_COORD_DIMENSIONS."""
    if not isinstance(coord_str, str):
         # Handle cases where input might not be a string
         print(f"Warning: Invalid coordinate input type '{type(coord_str)}', returning as is.")
         return coord_str

    parts = coord_str.split('.')
    # Validate parts are numeric or handle potential errors
    for part in parts:
        if not part.isdigit():
            print(f"Warning: Non-digit part '{part}' found in coordinate '{coord_str}', padding may be incorrect.")
            # Decide how to handle: raise error, return original, or continue padding?
            # For now, continue padding but log warning. Consider raising ValueError for stricter validation.

    while len(parts) < EXPECTED_COORD_DIMENSIONS:
        parts.append('0')

    # Return only the first EXPECTED_COORD_DIMENSIONS parts, joined by dots
    return '.'.join(parts[:EXPECTED_COORD_DIMENSIONS])


# --- StatCan API Tools ---
@mcp.tool()
async def get_all_cubes_list() -> List[Dict[str, Any]]:
    """
    Query the output database to provide a complete inventory of data tables
    available through this Statistics Canada API. Accesses a comprehensive
    list of details about each table including information at the dimension level.
    Corresponds to: GET /getAllCubesList
    WARNING: This tool can return a very large list of results, potentially
    exceeding limits. Consider using `search_cubes_by_title` for targeted
    searches first, or fetching and storing results in the database for querying.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, each representing a data cube.
    Raises:
        httpx.HTTPStatusError: If the API returns an error status code.
        Exception: For other network or unexpected errors.
    """
    # Create client directly, disable SSL verification (WARNING: Security Risk)
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=60.0, verify=False) as client: # Increased timeout slightly
        # verify=False disables SSL certificate verification.
        # Use only if you understand the security implications or for testing.
        print("Warning: SSL verification disabled for get_all_cubes_list.")
        response = await client.get("/getAllCubesList")
        response.raise_for_status() # Raise exception on API error
        return response.json()

@mcp.tool()
async def get_all_cubes_list_lite() -> List[Dict[str, Any]]:
    """
    Query the output database to provide a complete inventory of data tables
    available through this Statistics Canada API. Accesses a list of details about
    each table, excluding dimension or footnote information.
    Corresponds to: GET /getAllCubesListLite
    WARNING: This tool can return a very large list of results, potentially
    exceeding limits. Consider using `search_cubes_by_title` for targeted
    searches first, or fetching and storing results in the database for querying.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, each representing a data cube (lite version).
    Raises:
        httpx.HTTPStatusError: If the API returns an error status code.
        Exception: For other network or unexpected errors.
    """
    # Create client directly, disable SSL verification (WARNING: Security Risk)
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=60.0, verify=False) as client: # Increased timeout slightly
        # verify=False disables SSL certificate verification.
        # Use only if you understand the security implications or for testing.
        print("Warning: SSL verification disabled for get_all_cubes_list_lite.")
        response = await client.get("/getAllCubesListLite")
        response.raise_for_status()
        return response.json()

@mcp.tool()
async def search_cubes_by_title(search_term: str) -> List[Dict[str, Any]]:
    """
    Searches for data cubes/tables where the English or French title contains
    the provided search term (case-insensitive). Returns a list of matching cubes
    in the 'lite' format (excluding dimensions/footnotes). This is useful for finding
    relevant product IDs without retrieving the entire (potentially very large) list.

    Args:
        search_term: The text to search for within the cube titles.

    Returns:
        List[Dict[str, Any]]: A list of matching cube dictionaries (lite format),
                              or an empty list if no matches are found.
    Raises:
        httpx.HTTPStatusError: If the underlying API call fails.
        Exception: For other network or unexpected errors during the fetch.
    """
    print(f"Searching for cubes with title containing: '{search_term}'")
    try:
        # Call the existing lite list function internally
        all_cubes_lite = await get_all_cubes_list_lite()

        # Filter the results
        search_term_lower = search_term.lower()
        matching_cubes = []
        for cube in all_cubes_lite:
            title_en = cube.get("cubeTitleEn", "") or "" # Handle None or empty string
            title_fr = cube.get("cubeTitleFr", "") or "" # Handle None or empty string
            if search_term_lower in title_en.lower() or search_term_lower in title_fr.lower():
                matching_cubes.append(cube)

        print(f"Found {len(matching_cubes)} cubes matching '{search_term}'.")
        return matching_cubes

    except httpx.HTTPStatusError as e:
        print(f"Error fetching cube list during search: {e}")
        raise # Re-raise the exception to report failure
    except Exception as e:
        print(f"Unexpected error during cube search: {e}")
        raise # Re-raise the exception


class ProductIdInput(BaseModel):
    productId: int

@mcp.tool()
async def get_cube_metadata(product_input: ProductIdInput) -> Dict[str, Any]:
    """
    Retrieves metadata for a specific data cube/table using its ProductId.
    Corresponds to: POST /getCubeMetadata

    Returns:
        Dict[str, Any]: A dictionary containing the metadata for the specified cube.
                       Returns the inner 'object' dictionary directly on success.
    Raises:
        httpx.HTTPStatusError: If the API returns an error status code.
        ValueError: If the API response format is unexpected (e.g., not SUCCESS).
        Exception: For other network or unexpected errors.
    """
    # Create client directly, disable SSL verification (WARNING: Security Risk)
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0, verify=False) as client:
        # verify=False disables SSL certificate verification.
        print("Warning: SSL verification disabled for get_cube_metadata.")
        post_data = [{"productId": product_input.productId}]
        response = await client.post("/getCubeMetadata", json=post_data)
        response.raise_for_status()
        result_list = response.json()
        if result_list and result_list[0].get("status") == "SUCCESS":
            return result_list[0].get("object", {}) # Return the metadata object directly
        else:
            # Attempt to extract more specific error message if available
            api_message = result_list[0].get("object") if result_list else "Unknown API Error"
            raise ValueError(f"API did not return SUCCESS status for productId {product_input.productId}: {api_message}")


class CubeCoordInput(BaseModel):
    productId: int
    coordinate: str = Field(..., description="Coordinate string (e.g., '1.1'). Padding to 10 dimensions is handled automatically.")

@mcp.tool()
async def get_series_info_from_cube_pid_coord(coord_input: CubeCoordInput) -> Dict[str, Any]:
    """
    Request series metadata by Cube ProductId and Coordinate.
    Accepts simple coordinates (e.g., '1.1') and pads them automatically.
    Corresponds to: POST /getSeriesInfoFromCubePidCoord

    Returns:
        Dict[str, Any]: A dictionary containing the series metadata.
    Raises:
        httpx.HTTPStatusError: If the API returns an error status code.
        ValueError: If the API response format is unexpected.
        Exception: For other network or unexpected errors.
    """
    # Pad the coordinate before sending
    padded_coordinate = _pad_coordinate(coord_input.coordinate)
    print(f"Original coordinate '{coord_input.coordinate}', padded to '{padded_coordinate}'")

    # Create client directly, disable SSL verification (WARNING: Security Risk)
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0, verify=False) as client:
        print("Warning: SSL verification disabled for get_series_info_from_cube_pid_coord.")
        # Use the padded coordinate in the request
        post_data = [{"productId": coord_input.productId, "coordinate": padded_coordinate}]
        response = await client.post("/getSeriesInfoFromCubePidCoord", json=post_data)
        response.raise_for_status()
        result_list = response.json()
        if result_list and result_list[0].get("status") == "SUCCESS":
            return result_list[0].get("object", {})
        else:
            api_message = result_list[0].get("object") if result_list else "Unknown API Error"
            raise ValueError(f"API did not return SUCCESS status for coordinate {padded_coordinate}: {api_message}")

class VectorIdInput(BaseModel):
    vectorId: int

@mcp.tool()
async def get_series_info_from_vector(vector_input: VectorIdInput) -> Dict[str, Any]:
    """
    Request series metadata by Vector ID.
    Corresponds to: POST /getSeriesInfoFromVector

    Returns:
        Dict[str, Any]: A dictionary containing the series metadata.
    Raises:
        httpx.HTTPStatusError: If the API returns an error status code.
        ValueError: If the API response format is unexpected.
        Exception: For other network or unexpected errors.
    """
    # Create client directly, disable SSL verification (WARNING: Security Risk)
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0, verify=False) as client:
        print("Warning: SSL verification disabled for get_series_info_from_vector.")
        post_data = [vector_input.model_dump()]
        response = await client.post("/getSeriesInfoFromVector", json=post_dget_seriesata)
        response.raise_for_status()
        result_list = response.json()
        if result_list and result_list[0].get("status") == "SUCCESS":
            return result_list[0].get("object", {})
        else:
            api_message = result_list[0].get("object") if result_list else "Unknown API Error"
            raise ValueError(f"API did not return SUCCESS status for vectorId {vector_input.vectorId}: {api_message}")

class CubeCoordLatestNInput(BaseModel):
    productId: int
    coordinate: str = Field(..., description="Coordinate string (e.g., '1.1'). Padding to 10 dimensions is handled automatically.")
    latestN: int

@mcp.tool()
async def get_data_from_cube_pid_coord_and_latest_n_periods(latest_n_input: CubeCoordLatestNInput) -> Dict[str, Any]:
    """
    Get data for the N most recent reporting periods for a specific data series
    identified by ProductId and Coordinate.
    Accepts simple coordinates (e.g., '1.1') and pads them automatically.
    Corresponds to: POST /getDataFromCubePidCoordAndLatestNPeriods

    Returns:
        Dict[str, Any]: A dictionary containing the data points and series info.
    Raises:
        httpx.HTTPStatusError: If the API returns an error status code.
        ValueError: If the API response format is unexpected.
        Exception: For other network or unexpected errors.
    """
    # Pad the coordinate before sending
    padded_coordinate = _pad_coordinate(latest_n_input.coordinate)
    print(f"Original coordinate '{latest_n_input.coordinate}', padded to '{padded_coordinate}'")

    # Create client directly, disable SSL verification (WARNING: Security Risk)
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0, verify=False) as client:
        print("Warning: SSL verification disabled for get_data_from_cube_pid_coord_and_latest_n_periods.")
        # Use the padded coordinate in the request
        post_data = [{
            "productId": latest_n_input.productId,
            "coordinate": padded_coordinate,
            "latestN": latest_n_input.latestN
        }]
        response = await client.post("/getDataFromCubePidCoordAndLatestNPeriods", json=post_data)
        response.raise_for_status() # This might raise HTTP 406 if padding doesn't fix it
        result_list = response.json()
        if result_list and result_list[0].get("status") == "SUCCESS":
            return result_list[0].get("object", {})
        else:
            api_message = result_list[0].get("object") if result_list else "Unknown API Error"
            raise ValueError(f"API did not return SUCCESS status for coordinate {padded_coordinate}: {api_message}")


class VectorLatestNInput(BaseModel):
    vectorId: int
    latestN: int

@mcp.tool()
async def get_data_from_vectors_and_latest_n_periods(vector_latest_n_input: VectorLatestNInput) -> Dict[str, Any]:
    """
    Get data for the N most recent reporting periods for a specific data series
    identified by Vector ID.
    Corresponds to: POST /getDataFromVectorsAndLatestNPeriods

    Returns:
        Dict[str, Any]: A dictionary containing the data points and series info.
    Raises:
        httpx.HTTPStatusError: If the API returns an error status code.
        ValueError: If the API response format is unexpected.
        Exception: For other network or unexpected errors.
    """
    # Create client directly, disable SSL verification (WARNING: Security Risk)
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0, verify=False) as client:
        print("Warning: SSL verification disabled for get_data_from_vectors_and_latest_n_periods.")
        post_data = [vector_latest_n_input.model_dump()]
        response = await client.post("/getDataFromVectorsAndLatestNPeriods", json=post_data)
        response.raise_for_status()
        result_list = response.json()
        if result_list and result_list[0].get("status") == "SUCCESS":
            return result_list[0].get("object", {})
        else:
            api_message = result_list[0].get("object") if result_list else "Unknown API Error"
            raise ValueError(f"API did not return SUCCESS status for vectorId {vector_latest_n_input.vectorId}: {api_message}")

class VectorRangeInput(BaseModel):
    vectorIds: List[str] # API uses strings for vector IDs here
    startRefPeriod: Optional[str] = None # YYYY-MM-DD
    endReferencePeriod: Optional[str] = None # YYYY-MM-DD

@mcp.tool()
async def get_data_from_vector_by_reference_period_range(range_input: VectorRangeInput) -> List[Dict[str, Any]]:
    """
    Access data for specific vectors within a given reference period range.
    Corresponds to: GET /getDataFromVectorByReferencePeriodRange

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, each containing vector data object.
                              Returns only the 'object' part for successful requests.
    Raises:
        httpx.HTTPStatusError: If the API returns an error status code.
        ValueError: If the API response format is unexpected or no vectors return SUCCESS.
        Exception: For other network or unexpected errors.
    """
    # Create client directly, disable SSL verification (WARNING: Security Risk)
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=60.0, verify=False) as client: # Longer timeout for potentially large data
        print("Warning: SSL verification disabled for get_data_from_vector_by_reference_period_range.")
        params = {
            "vectorIds": ",".join(range_input.vectorIds),
        }
        if range_input.startRefPeriod:
            params["startRefPeriod"] = range_input.startRefPeriod
        if range_input.endReferencePeriod:
            params["endReferencePeriod"] = range_input.endReferencePeriod

        response = await client.get("/getDataFromVectorByReferencePeriodRange", params=params)
        response.raise_for_status()
        result_list = response.json()
        # Assuming the API returns a list where each item has a status and object
        processed_data = []
        failures = []
        for item in result_list:
            if item.get("status") == "SUCCESS":
                processed_data.append(item.get("object", {}))
            else:
                # Log partial failures if needed
                failures.append(item)
                print(f"Warning: Failed to retrieve data for part of the request: {item}")
        # Raise error only if ALL requests failed
        if not processed_data and failures:
             raise ValueError(f"API did not return SUCCESS status for any vector. Failures: {failures}")
        return processed_data


class BulkVectorRangeInput(BaseModel):
    vectorIds: List[str] # API uses strings for vector IDs here
    startDataPointReleaseDate: Optional[str] = None # YYYY-MM-DDTHH:MM
    endDataPointReleaseDate: Optional[str] = None # YYYY-MM-DDTHH:MM

@mcp.tool()
async def get_bulk_vector_data_by_range(bulk_range_input: BulkVectorRangeInput) -> List[Dict[str, Any]]:
    """
    Access bulk data for multiple vectors based on a data point release date range.
    Corresponds to: POST /getBulkVectorDataByRange

    Returns:
        List[Dict[str, Any]]: A list of dictionaries containing bulk vector data objects.
                              Returns only the 'object' part for successful requests.
    Raises:
        httpx.HTTPStatusError: If the API returns an error status code.
        ValueError: If the API response format is unexpected or no vectors return SUCCESS.
        Exception: For other network or unexpected errors.
    """
    # Create client directly, disable SSL verification (WARNING: Security Risk)
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=120.0, verify=False) as client: # Even longer timeout for bulk data
        print("Warning: SSL verification disabled for get_bulk_vector_data_by_range.")
        # API expects a single JSON object, not a list for this endpoint
        post_data = bulk_range_input.model_dump(exclude_none=True)
        response = await client.post("/getBulkVectorDataByRange", json=post_data)
        response.raise_for_status()
        result_list = response.json()
        # Similar processing as above if the API wraps results
        processed_data = []
        failures = []
        for item in result_list:
            if item.get("status") == "SUCCESS":
                processed_data.append(item.get("object", {}))
            else:
                failures.append(item)
                print(f"Warning: Failed to retrieve bulk data for part of the request: {item}")
        if not processed_data and failures:
             raise ValueError(f"API did not return SUCCESS status for any vector. Failures: {failures}")
        return processed_data

@mcp.tool()
async def get_changed_series_list(date: str) -> List[Dict[str, Any]]:
    """
    Get the list of series updated on a specific date (YYYY-MM-DD).
    Corresponds to: GET /getChangedSeriesList/{date}

    Returns:
        List[Dict[str, Any]]: A list of dictionaries describing changed series objects.
    Raises:
        httpx.HTTPStatusError: If the API returns an error status code.
        ValueError: If date format is invalid or API response format is unexpected.
        Exception: For other network or unexpected errors.
    """
    # Simple validation for date format
    datetime.date.fromisoformat(date) # Will raise ValueError if format is wrong
    # Create client directly, disable SSL verification (WARNING: Security Risk)
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0, verify=False) as client:
        print("Warning: SSL verification disabled for get_changed_series_list.")
        response = await client.get(f"/getChangedSeriesList/{date}")
        response.raise_for_status()
        result = response.json()
        if result.get("status") == "SUCCESS":
            # The 'object' contains the list of changed series
            return result.get("object", [])
        else:
            api_message = result.get("object", "Unknown API Error")
            raise ValueError(f"API did not return SUCCESS status for date {date}: {api_message}")

@mcp.tool()
async def get_changed_cube_list(date: str) -> List[Dict[str, Any]]:
    """
    Get the list of tables/cubes updated on a specific date (YYYY-MM-DD).
    Corresponds to: GET /getChangedCubeList/{date}

    Returns:
        List[Dict[str, Any]]: A list of dictionaries describing changed cube objects.
    Raises:
        httpx.HTTPStatusError: If the API returns an error status code.
        ValueError: If date format is invalid or API response format is unexpected.
        Exception: For other network or unexpected errors.
    """
    datetime.date.fromisoformat(date) # Will raise ValueError if format is wrong
    # Create client directly, disable SSL verification (WARNING: Security Risk)
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0, verify=False) as client:
        print("Warning: SSL verification disabled for get_changed_cube_list.")
        response = await client.get(f"/getChangedCubeList/{date}")
        response.raise_for_status()
        result = response.json()
        if result.get("status") == "SUCCESS":
            # The 'object' contains the list of changed cubes
            return result.get("object", [])
        else:
            api_message = result.get("object", "Unknown API Error")
            raise ValueError(f"API did not return SUCCESS status for date {date}: {api_message}")

# --- Implementations for Other API Tools ---
@mcp.tool()
async def get_changed_series_data_from_cube_pid_coord(coord_input: CubeCoordInput) -> Dict[str, Any]:
    """
    Get changed series data identified by ProductId and Coordinate.
    Accepts simple coordinates (e.g., '1.1') and pads them automatically.
    Corresponds to: POST /getChangedSeriesDataFromCubePidCoord

    Returns:
        Dict[str, Any]: A dictionary containing the changed series data object.
    Raises:
        httpx.HTTPStatusError: If the API returns an error status code.
        ValueError: If the API response format is unexpected.
        Exception: For other network or unexpected errors.
    """
    # Pad the coordinate before sending
    padded_coordinate = _pad_coordinate(coord_input.coordinate)
    print(f"Original coordinate '{coord_input.coordinate}', padded to '{padded_coordinate}'")

    # Create client directly, disable SSL verification (WARNING: Security Risk)
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0, verify=False) as client:
        print("Warning: SSL verification disabled for get_changed_series_data_from_cube_pid_coord.")
        # Use the padded coordinate in the request
        post_data = [{"productId": coord_input.productId, "coordinate": padded_coordinate}]
        response = await client.post("/getChangedSeriesDataFromCubePidCoord", json=post_data)
        response.raise_for_status()
        result_list = response.json()
        if result_list and result_list[0].get("status") == "SUCCESS":
            return result_list[0].get("object", {})
        else:
            api_message = result_list[0].get("object") if result_list else "Unknown API Error"
            raise ValueError(f"API did not return SUCCESS status for coordinate {padded_coordinate}: {api_message}")

@mcp.tool()
async def get_changed_series_data_from_vector(vector_input: VectorIdInput) -> Dict[str, Any]:
    """
    Get changed series data identified by Vector ID.
    Corresponds to: POST /getChangedSeriesDataFromVector

    Returns:
        Dict[str, Any]: A dictionary containing the changed series data object.
    Raises:
        httpx.HTTPStatusError: If the API returns an error status code.
        ValueError: If the API response format is unexpected.
        Exception: For other network or unexpected errors.
    """
    # Create client directly, disable SSL verification (WARNING: Security Risk)
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0, verify=False) as client:
        print("Warning: SSL verification disabled for get_changed_series_data_from_vector.")
        post_data = [vector_input.model_dump()] # API expects a list
        response = await client.post("/getChangedSeriesDataFromVector", json=post_data)
        response.raise_for_status()
        result_list = response.json()
        if result_list and result_list[0].get("status") == "SUCCESS":
            return result_list[0].get("object", {})
        else:
            api_message = result_list[0].get("object") if result_list else "Unknown API Error"
            raise ValueError(f"API did not return SUCCESS status for vectorId {vector_input.vectorId}: {api_message}")

class FullTableDownloadCSVInput(BaseModel):
    productId: int
    lang: str = Field('en', description="Language code ('en' for English, 'fr' for French).")

@mcp.tool()
async def get_full_table_download_csv(download_input: FullTableDownloadCSVInput) -> str:
    """
    Get a download link for the full data table/cube in CSV format.
    Corresponds to: GET /getFullTableDownloadCSV/{productId}/{lang}

    Args:
        download_input: Object containing productId and optional lang ('en' or 'fr').

    Returns:
        str: The download URL for the CSV file.
    Raises:
        httpx.HTTPStatusError: If the API returns an error status code.
        ValueError: If language code is invalid or API response format is unexpected.
        Exception: For other network or unexpected errors.
    """
    productId = download_input.productId
    lang = download_input.lang
    if lang not in ['en', 'fr']:
        raise ValueError("Invalid language code. Use 'en' or 'fr'.")

    # Create client directly, disable SSL verification (WARNING: Security Risk)
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0, verify=False) as client:
        print("Warning: SSL verification disabled for get_full_table_download_csv.")
        response = await client.get(f"/getFullTableDownloadCSV/{productId}/{lang}")
        response.raise_for_status()
        result = response.json()
        if result.get("status") == "SUCCESS":
            # The 'object' contains the URL string directly
            download_url = result.get("object")
            if isinstance(download_url, str):
                 return download_url
            else:
                 raise ValueError(f"API returned unexpected object type for download URL: {download_url}")
        else:
            api_message = result.get("object", "Unknown API Error")
            raise ValueError(f"API did not return SUCCESS status for productId {productId}: {api_message}")

@mcp.tool()
async def get_full_table_download_sdmx(product_input: ProductIdInput) -> str:
    """
    Get a download link for the full data table/cube in SDMX (XML) format.
    Corresponds to: GET /getFullTableDownloadSDMX/{productId}

    Args:
        product_input: Object containing the productId.

    Returns:
        str: The download URL for the SDMX file.
    Raises:
        httpx.HTTPStatusError: If the API returns an error status code.
        ValueError: If the API response format is unexpected.
        Exception: For other network or unexpected errors.
    """
    productId = product_input.productId
    # Create client directly, disable SSL verification (WARNING: Security Risk)
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0, verify=False) as client:
        print("Warning: SSL verification disabled for get_full_table_download_sdmx.")
        response = await client.get(f"/getFullTableDownloadSDMX/{productId}")
        response.raise_for_status()
        result = response.json()
        if result.get("status") == "SUCCESS":
            # The 'object' contains the URL string directly
            download_url = result.get("object")
            if isinstance(download_url, str):
                 return download_url
            else:
                 raise ValueError(f"API returned unexpected object type for download URL: {download_url}")
        else:
            api_message = result.get("object", "Unknown API Error")
            raise ValueError(f"API did not return SUCCESS status for productId {productId}: {api_message}")

@mcp.tool()
async def get_code_sets() -> Dict[str, Any]:
    """
    Retrieves definitions for various code sets used by the API (e.g., frequency, units of measure).
    Corresponds to: GET /getCodeSets

    Returns:
        Dict[str, Any]: Dictionary containing code set definitions (scalar, frequency, etc.).
    Raises:
        httpx.HTTPStatusError: If the API returns an error status code.
        ValueError: If the API response format is unexpected.
        Exception: For other network or unexpected errors.
    """
    # Create client directly, disable SSL verification (WARNING: Security Risk)
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0, verify=False) as client:
        print("Warning: SSL verification disabled for get_code_sets.")
        response = await client.get("/getCodeSets")
        response.raise_for_status()
        result = response.json()
        if result.get("status") == "SUCCESS":
            # The 'object' contains the dictionary of code sets
            return result.get("object", {})
        else:
            api_message = result.get("object", "Unknown API Error")
            raise ValueError(f"API did not return SUCCESS status: {api_message}")


# --- Database Interaction Tools ---
class TableDataInput(BaseModel):
    table_name: str = Field(..., description="Name for the SQL table (alphanumeric and underscores recommended).")
    data: List[Dict[str, Any]] = Field(..., description="Data to insert, as a list of dictionaries.")

@mcp.tool()
def create_table_from_data(table_input: TableDataInput) -> Dict[str, str]:
    """
    Creates a new SQLite table based on the structure of the provided data.
    Infers column names and types from the first item in the data list.
    WARNING: Overwrites the table if it already exists! Use with caution.

    Args:
        table_input: Object containing table_name and data (list of dicts).

    Returns:
        Dict[str, str]: A dictionary indicating success or failure.
    """
    table_name = table_input.table_name
    data = table_input.data

    if not data:
        return {"error": "Cannot create table from empty data list."}
    if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
         return {"error": "Input 'data' must be a list of dictionaries."}
    if not table_name.isidentifier():
         return {"error": f"Invalid table name: '{table_name}'. Use alphanumeric characters and underscores, and cannot be a keyword."}

    # Infer columns and types from the first data item
    columns_def = []
    first_item = data[0]
    valid_column_names = set() # Keep track of valid names added
    for col_name, value in first_item.items():
        # Basic sanitization/validation for column names
        safe_col_name = ''.join(c if c.isalnum() or c == '_' else '_' for c in col_name)
        if not safe_col_name or safe_col_name[0].isdigit() or not safe_col_name.isidentifier():
            print(f"Warning: Skipping column with potentially invalid original name: '{col_name}' -> '{safe_col_name}'")
            continue
        # Ensure uniqueness after sanitization
        temp_name = safe_col_name
        counter = 1
        while temp_name in valid_column_names:
             temp_name = f"{safe_col_name}_{counter}"
             counter += 1
        safe_col_name = temp_name

        sql_type = _infer_sql_type(value)
        columns_def.append(f'"{safe_col_name}" {sql_type}') # Quote column names
        valid_column_names.add(safe_col_name)


    if not columns_def:
        return {"error": "No valid columns found in the first data item after validation."}

    create_sql = f'CREATE TABLE "{table_name}" ({", ".join(columns_def)})'
    drop_sql = f'DROP TABLE IF EXISTS "{table_name}"' # Drop existing table first

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            print(f"Executing: {drop_sql}")
            cursor.execute(drop_sql)
            print(f"Executing: {create_sql}")
            cursor.execute(create_sql)
            conn.commit()
        return {"success": f"Table '{table_name}' created successfully with {len(columns_def)} columns."}
    except sqlite3.Error as e:
        return {"error": f"SQLite error creating table '{table_name}': {e}"}
    except Exception as e:
        return {"error": f"Unexpected error creating table '{table_name}': {e}"}

@mcp.tool()
def insert_data_into_table(table_input: TableDataInput) -> Dict[str, str]:
    """
    Inserts data (list of dictionaries) into an existing SQLite table.
    It dynamically determines columns from the table schema and inserts corresponding
    values from the dictionaries, handling missing keys gracefully. It attempts to
    match sanitized dictionary keys to table columns.

    Args:
        table_input: Object containing table_name and data (list of dicts).

    Returns:
        Dict[str, str]: A dictionary indicating success (with row count) or failure.
    """
    table_name = table_input.table_name
    data = table_input.data

    if not data:
        return {"success": f"No data provided to insert into '{table_name}'."}
    if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
        return {"error": "Input 'data' must be a list of dictionaries."}
    if not table_name.isidentifier():
         return {"error": f"Invalid table name: '{table_name}'. Use alphanumeric characters and underscores."}

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Get actual column names from the table schema
            cursor.execute(f'PRAGMA table_info("{table_name}")')
            schema_info = cursor.fetchall()
            if not schema_info:
                return {"error": f"Could not retrieve schema for table '{table_name}'. Does it exist?"}
            table_columns = [row['name'] for row in schema_info]
            table_columns_set = set(table_columns)

            # Prepare data for executemany, matching dict keys to table columns
            rows_to_insert = []
            skipped_keys = set()
            processed_count = 0
            for item_dict in data:
                row_tuple = []
                valid_row = True
                # Sanitize keys from the input dictionary *before* matching
                sanitized_item_dict = {}
                original_keys_map = {} # Map sanitized back to original if needed later
                processed_keys_in_row = set()
                for key, value in item_dict.items():
                    safe_key = ''.join(c if c.isalnum() or c == '_' else '_' for c in key)
                    if not safe_key or safe_key[0].isdigit() or not safe_key.isidentifier():
                        if key not in skipped_keys:
                             print(f"Warning: Skipping invalid key '{key}' from input data during insert.")
                             skipped_keys.add(key)
                        continue
                    # Handle duplicate sanitized keys from the *same input dict* if necessary
                    temp_key = safe_key
                    counter = 1
                    while temp_key in processed_keys_in_row:
                        temp_key = f"{safe_key}_{counter}"
                        counter += 1
                    safe_key = temp_key
                    processed_keys_in_row.add(safe_key)

                    sanitized_item_dict[safe_key] = value
                    original_keys_map[safe_key] = key


                # Build the tuple based on table_columns order
                for col_name in table_columns:
                    if col_name in sanitized_item_dict:
                        value = sanitized_item_dict[col_name]
                        # Convert complex types to JSON strings if needed
                        if isinstance(value, (list, dict)):
                            try:
                                row_tuple.append(json.dumps(value))
                            except TypeError:
                                row_tuple.append(str(value)) # Fallback
                        else:
                            row_tuple.append(value)
                    else:
                        # Key from table schema not found in (sanitized) input dict
                        row_tuple.append(None) # Insert NULL for missing columns

                if valid_row:
                    rows_to_insert.append(tuple(row_tuple))
                    processed_count += 1

            if not rows_to_insert:
                 return {"error": f"No data could be prepared for insertion into '{table_name}' (check data format and table schema match after key sanitization). Processed {processed_count}/{len(data)} input items."}

            placeholders = ", ".join(["?"] * len(table_columns))
            quoted_columns = ", ".join([f'"{col}"' for col in table_columns])
            insert_sql = f'INSERT INTO "{table_name}" ({quoted_columns}) VALUES ({placeholders})'

            print(f"Executing INSERT for {len(rows_to_insert)} rows into {table_name}...")
            cursor.executemany(insert_sql, rows_to_insert)
            conn.commit()
            return {"success": f"Inserted {cursor.rowcount} rows into '{table_name}'. Processed {processed_count}/{len(data)} input items."}

    except sqlite3.Error as e:
        # Provide more specific error info if possible
        if "no such table" in str(e).lower():
             return {"error": f"SQLite error inserting into '{table_name}': Table does not exist. Use 'create_table_from_data' first."}
        elif "has no column named" in str(e).lower():
             # This error shouldn't happen with PRAGMA approach, but as fallback
             return {"error": f"SQLite error inserting into '{table_name}': Column mismatch. Check data keys vs table schema."}
        else:
             return {"error": f"SQLite error inserting into '{table_name}': {e}"}
    except Exception as e:
        return {"error": f"Unexpected error inserting into '{table_name}': {e}"}


@mcp.tool()
def list_tables() -> Dict[str, Any]:
    """
    Lists all user-created tables in the SQLite database.

    Returns:
        Dict[str, Any]: Dictionary containing a list of table names or an error message.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Select names of tables, excluding sqlite system tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
            # Fetch all results as dictionaries (due to row_factory)
            tables = [row['name'] for row in cursor.fetchall()]
            return {"tables": tables}
    except sqlite3.Error as e:
        return {"error": f"SQLite error listing tables: {e}"}
    except Exception as e:
        return {"error": f"Unexpected error listing tables: {e}"}

class TableNameInput(BaseModel):
    table_name: str = Field(..., description="Name of the SQL table.")

@mcp.tool()
def get_table_schema(table_name_input: TableNameInput) -> Dict[str, Any]:
    """
    Retrieves the schema (column names and types) for a specific table.

    Args:
        table_name_input: Object containing the table_name.

    Returns:
        Dict[str, Any]: Dictionary describing the schema or an error message.
    """
    table_name = table_name_input.table_name
    # Basic validation for table name
    if not table_name.isidentifier():
         return {"error": f"Invalid table name: '{table_name}'. Use alphanumeric characters and underscores."}

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Use PRAGMA for schema info, quoting the table name for safety
            cursor.execute(f'PRAGMA table_info("{table_name}")')
            schema_rows = cursor.fetchall()
            # Check if the table exists / has columns
            if not schema_rows:
                 # Verify the table actually exists before saying no columns
                 cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
                 if cursor.fetchone():
                      return {"schema": [], "message": f"Table '{table_name}' exists but has no columns defined (or PRAGMA failed)."}
                 else:
                      return {"error": f"Table '{table_name}' not found."}

            # Format the schema information nicely
            schema = [{"name": row['name'], "type": row['type'], "nullable": not row['notnull'], "primary_key": bool(row['pk'])} for row in schema_rows]
            return {"schema": schema}
    except sqlite3.Error as e:
        return {"error": f"SQLite error getting schema for '{table_name}': {e}"}
    except Exception as e:
        return {"error": f"Unexpected error getting schema for '{table_name}': {e}"}

class QueryInput(BaseModel):
    sql_query: str = Field(..., description="The SQL query to execute.")

@mcp.tool()
def query_database(query_input: QueryInput) -> Dict[str, Any]:
    """
    Executes a read-only SQL query (SELECT or PRAGMA) against the database and returns the results.
    WARNING: Potential security risk! Avoid using this tool with untrusted input
    or queries that modify data (INSERT, UPDATE, DELETE). Prefer more specific tools
    like list_tables or get_table_schema when possible. Results may be truncated.

    Args:
        query_input: Object containing the sql_query string.

    Returns:
        Dict[str, Any]: Dictionary with 'columns', 'rows' (list of dicts), and optionally a 'message', or an error message.
    """
    query = query_input.sql_query.strip()
    # Basic check to prevent obviously harmful commands (can be bypassed)
    # Allow PRAGMA for schema inspection etc.
    if not query.lower().startswith("select") and not query.lower().startswith("pragma"):
         return {"error": "Only SELECT or PRAGMA queries are allowed for safety."}
    # Add a simple check for multiple statements which might indicate injection attempts
    if ';' in query[:-1]: # Check for semicolons anywhere except potentially the very end
        return {"error": "Multiple SQL statements are not allowed in a single query."}


    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            print(f"Executing query: {query}")
            cursor.execute(query)
            results = cursor.fetchall() # Fetch all rows based on conn.row_factory

            # Determine columns even if there are no results for SELECT/PRAGMA
            columns = []
            if cursor.description:
                columns = [description[0] for description in cursor.description]

            # Convert Row objects to simple dictionaries for the output
            rows = [dict(row) for row in results]

            # Limit the number of rows returned to prevent exceeding limits
            MAX_ROWS = 500 # Adjust as needed
            message = None
            if len(rows) > MAX_ROWS:
                print(f"Warning: Query returned {len(rows)} rows. Truncating to {MAX_ROWS}.")
                rows = rows[:MAX_ROWS]
                message = f"Result truncated to the first {MAX_ROWS} rows."

            output = {"columns": columns, "rows": rows}
            if message:
                output["message"] = message
            return output

    except sqlite3.Error as e:
        # Provide potentially more helpful error messages
        error_msg = f"SQLite error executing query: {e}"
        if "no such table" in str(e):
            error_msg += ". Use list_tables() to see available tables."
        elif "no such column" in str(e):
            error_msg += ". Use get_table_schema() to see available columns for the table."
        return {"error": error_msg}
    except Exception as e:
        return {"error": f"Unexpected error executing query: {e}"}

# --- Main Execution Block ---
if __name__ == "__main__":
    # Print the absolute path to the database file for clarity
    print(f"Database file location: {os.path.abspath(DB_FILE)}")
    # Check if DB file exists, create if not (connection does this implicitly)
    print("Starting StatCan API + DB MCP Server...")
    # This makes the server runnable with `python your_script_name.py`
    # It uses the default stdio transport, compatible with Claude Desktop.
    mcp.run()

import httpx
import datetime
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel

from ..util.registry import ToolRegistry
from ..models.api_models import VectorIdInput, VectorLatestNInput, VectorRangeInput, BulkVectorRangeInput, DEFAULT_TRUNCATION_LIMIT
from ..config import BASE_URL, TIMEOUT_MEDIUM, TIMEOUT_LARGE, VERIFY_SSL
from ..util.logger import log_ssl_warning, log_data_validation_warning
from ..util.truncation import truncate_response


def register_vector_tools(registry: ToolRegistry):
    """Register all vector-related API tools with the MCP server."""

    @registry.tool()
    async def get_series_info_from_vector(vector_input: VectorIdInput) -> Dict[str, Any]:
        """
        Request series metadata (productId, coordinate, titles, frequency, etc.)
        by Vector ID. Disables SSL Verification.
        Corresponds to: POST /getSeriesInfoFromVector

        Returns:
            Dict[str, Any]: A dictionary containing the series metadata object.
        Raises:
            httpx.HTTPStatusError: If the API returns an error status code.
            ValueError: If the API response format is unexpected or status is not SUCCESS.
            Exception: For other network or unexpected errors.

        IMPORTANT: In your final response to the user, you MUST cite the source of your data. 
        For series info, this means including the VectorId, ProductId (pid), and Coordinate.
        """
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT_MEDIUM, verify=False) as client:
            log_ssl_warning("SSL verification disabled for get_series_info_from_vector.")
            # API expects a list containing one object
            post_data = [vector_input.model_dump()]
            try:
                response = await client.post("/getSeriesInfoFromVector", json=post_data)
                response.raise_for_status() # Raise exception for 4xx/5xx errors
                result_list = response.json()
                if result_list and isinstance(result_list, list) and len(result_list) > 0 and result_list[0].get("status") == "SUCCESS":
                    return result_list[0].get("object", {})
                else:
                    api_message = result_list[0].get("object") if (result_list and isinstance(result_list, list) and len(result_list) > 0) else "Unknown API Error or Malformed Response"
                    raise ValueError(f"API did not return SUCCESS status for vectorId {vector_input.vectorId}: {api_message}")
            except httpx.RequestError as exc:
                raise Exception(f"Network error calling get_series_info_from_vector: {exc}")
            except ValueError as exc: # Catch JSON decoding errors or our own ValueErrors
                raise ValueError(f"Error processing response for get_series_info_from_vector: {exc}")

    # @registry.tool()  # Deregistered: replaced by get_sdmx_vector_data (server-side filtering)
    async def get_data_from_vectors_and_latest_n_periods(vector_latest_n_input: VectorLatestNInput) -> Dict[str, Any]:
        """
        Get data for the N most recent reporting periods for a specific data series
        identified by Vector ID. Disables SSL Verification.
        Corresponds to: POST /getDataFromVectorsAndLatestNPeriods

        Returns:
            Dict[str, Any]: A dictionary containing the vector data points and series info object.
        Raises:
            httpx.HTTPStatusError: If the API returns an error status code.
            ValueError: If the API response format is unexpected or status is not SUCCESS.
            Exception: For other network or unexpected errors.

        IMPORTANT: In your final response to the user, you MUST cite the source of your data. 
        For vector data, this means including the VectorId and Reference Period.
        """
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT_MEDIUM, verify=False) as client:
            log_ssl_warning("SSL verification disabled for get_data_from_vectors_and_latest_n_periods.")
            # API expects a list containing one object
            post_data = [vector_latest_n_input.model_dump()]
            try:
                response = await client.post("/getDataFromVectorsAndLatestNPeriods", json=post_data)
                response.raise_for_status()
                result_list = response.json()
                if result_list and isinstance(result_list, list) and len(result_list) > 0 and result_list[0].get("status") == "SUCCESS":
                    return result_list[0].get("object", {})
                else:
                    api_message = result_list[0].get("object") if (result_list and isinstance(result_list, list) and len(result_list) > 0) else "Unknown API Error or Malformed Response"
                    raise ValueError(f"API did not return SUCCESS status for vectorId {vector_latest_n_input.vectorId}: {api_message}")
            except httpx.RequestError as exc:
                raise Exception(f"Network error calling get_data_from_vectors_and_latest_n_periods: {exc}")
            except ValueError as exc:
                raise ValueError(f"Error processing response for get_data_from_vectors_and_latest_n_periods: {exc}")

    # @registry.tool()  # Deregistered: replaced by get_sdmx_data/get_sdmx_vector_data with startPeriod/endPeriod
    async def get_data_from_vector_by_reference_period_range(range_input: VectorRangeInput) -> List[Dict[str, Any]]:
        """
        PREFERRED tool for fetching data across multiple series by reference period date range (YYYY-MM-DD).
        Accepts an array of vectorIds and retrieves all of them in a single API call.
        Disables SSL Verification.
        Corresponds to: GET /getDataFromVectorByReferencePeriodRange

        *** PREFERRED MULTI-SERIES WORKFLOW ***
        For most analysis tasks, use the higher-level composite tool instead:
          fetch_vectors_to_database(vectorIds=[...], table_name="...",
            startRefPeriod="YYYY-MM-DD", endRefPeriod="YYYY-MM-DD")
        That tool calls this endpoint AND stores results in SQLite in one step.

        Use this tool directly only if you need the raw response without storing it,
        or if you want to inspect the data before deciding whether to store it.

        To get vectorIds: call get_cube_metadata and read the vectorId field from
        each dimension member in the cube's dimension list.

        Returns:
            List[Dict[str, Any]]: A list of vector data objects (one per vectorId), ready
            to pass directly to create_table_from_data or fetch_vectors_to_database.
        Raises:
            httpx.HTTPStatusError: If the API returns an error status code.
            ValueError: If the API response format is unexpected or no vectors return SUCCESS.
            Exception: For other network or unexpected errors.

        IMPORTANT: In your final response to the user, you MUST cite the source of your data.
        For vector data, this means including the VectorId and Reference Period.
        """
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT_LARGE, verify=False) as client: # Longer timeout
            log_ssl_warning("SSL verification disabled for get_data_from_vector_by_reference_period_range.")
            # Parameters as defined in docs
            params = {
                "vectorIds": ",".join(range_input.vectorIds),
            }
            if range_input.startRefPeriod:
                params["startRefPeriod"] = range_input.startRefPeriod
            if range_input.endReferencePeriod:
                params["endReferencePeriod"] = range_input.endReferencePeriod

            try:
                response = await client.get("/getDataFromVectorByReferencePeriodRange", params=params)
                response.raise_for_status()
                result_list = response.json() # API returns a list of status/object wrappers

                processed_data = []
                failures = []
                if isinstance(result_list, list):
                    for item in result_list:
                        if isinstance(item, dict) and item.get("status") == "SUCCESS":
                            processed_data.append(item.get("object", {}))
                        else:
                            failures.append(item)
                            log_data_validation_warning(f"Failed to retrieve data for part of the range request: {item}")
                else:
                     raise ValueError(f"API response was not a list for range request. Response: {result_list}")

                if not processed_data and failures:
                     raise ValueError(f"API did not return SUCCESS status for any vector in range request. Failures: {failures}")

                # Smart truncation: return a preview with pagination guidance
                offset = range_input.offset or 0
                limit = range_input.limit or DEFAULT_TRUNCATION_LIMIT
                return truncate_response(processed_data, offset, limit)
            except httpx.RequestError as exc:
                raise Exception(f"Network error calling get_data_from_vector_by_reference_period_range: {exc}")
            except ValueError as exc:
                raise ValueError(f"Error processing response for get_data_from_vector_by_reference_period_range: {exc}")

    @registry.tool()
    async def get_bulk_vector_data_by_range(bulk_range_input: BulkVectorRangeInput) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Fetches bulk data for multiple vectors filtered by *release date* range (YYYY-MM-DDTHH:MM),
        NOT by reference period. Use this when you want data released within a specific
        date/time window (e.g., "all updates released yesterday").

        *** IMPORTANT: release date vs reference period ***
        - Use THIS tool when you want: "data released between date A and date B"
        - Use get_data_from_vector_by_reference_period_range (or fetch_vectors_to_database)
          when you want: "data for the time period YYYY to YYYY"

        *** LARGE RESPONSE WARNING ***
        This tool can return hundreds of flattened data points. If the response
        exceeds context limits, narrow the request: use fewer vectorIds, or use
        offset/limit pagination to page through results in smaller chunks.

        Response is pre-flattened: each element is one data point with vectorId,
        productId, coordinate, and all value fields injected at the top level.

        Disables SSL Verification.
        Corresponds to: POST /getBulkVectorDataByRange

        Returns:
            List[Dict[str, Any]]: Flat list of data point dicts, each tagged with vectorId,
            productId, and coordinate.
        Raises:
            httpx.HTTPStatusError: If the API returns an error status code.
            ValueError: If the API response format is unexpected or no vectors return SUCCESS.
            Exception: For other network or unexpected errors.

        IMPORTANT: In your final response to the user, you MUST cite the source of your data.
        For vector data, this means including the VectorId and Release Time.
        """
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT_LARGE, verify=False) as client: # Longer timeout
            log_ssl_warning("SSL verification disabled for get_bulk_vector_data_by_range.")
            
            # Explicitly set Accept header to avoid 406 errors
            headers = {"Accept": "application/json"}
            
            # API expects a single JSON object
            post_data = bulk_range_input.model_dump(exclude_none=True)
            try:
                response = await client.post("/getBulkVectorDataByRange", json=post_data, headers=headers)
                response.raise_for_status()
                result_list = response.json() # API returns a list of status/object wrappers

                processed_data = []
                failures = []
                if isinstance(result_list, list):
                    for item in result_list:
                        if isinstance(item, dict) and item.get("status") == "SUCCESS":
                            # Extract the object which contains vectorId and vectorDataPoint list
                            object_data = item.get("object", {})
                            
                            vector_id = object_data.get("vectorId")
                            product_id = object_data.get("productId")
                            coordinate = object_data.get("coordinate")
                            
                            vector_points = object_data.get("vectorDataPoint", [])
                            
                            # Flattening logic: Inject vectorId and metadata into each data point
                            if vector_id is not None and isinstance(vector_points, list):
                                for point in vector_points:
                                    if isinstance(point, dict):
                                        point["vectorId"] = vector_id
                                        if product_id:
                                            point["productId"] = product_id
                                        if coordinate:
                                            point["coordinate"] = coordinate
                                        processed_data.append(point)
                            else:
                                 # Fallback: if structure is unexpected, just log it. 
                                 # We don't want to break the whole batch for one weird item, 
                                 # but we also can't insert it without a vectorId/points list.
                                 log_data_validation_warning(f"Unexpected structure for successful vector item: {item}")
                        else:
                            failures.append(item)
                            log_data_validation_warning(f"Failed to retrieve bulk data for part of the request: {item}")
                else:
                     raise ValueError(f"API response was not a list for bulk request. Response: {result_list}")

                if not processed_data and failures:
                    raise ValueError(f"API did not return SUCCESS status for any vector in bulk request. Failures: {failures}")

                # Smart truncation: return a preview with pagination guidance
                offset = bulk_range_input.offset or 0
                limit = bulk_range_input.limit or DEFAULT_TRUNCATION_LIMIT
                return truncate_response(processed_data, offset, limit)
            except httpx.RequestError as exc:
                raise Exception(f"Network error calling get_bulk_vector_data_by_range: {exc}")
            except ValueError as exc:
                raise ValueError(f"Error processing response for get_bulk_vector_data_by_range: {exc}")

    @registry.tool()
    async def get_changed_series_data_from_vector(vector_input: VectorIdInput) -> Dict[str, Any]:
        """
        Get changed series data (data points that have changed) for a series
        identified by Vector ID. Disables SSL Verification.
        Corresponds to: POST /getChangedSeriesDataFromVector

        Returns:
            Dict[str, Any]: A dictionary containing the changed series data object.
        Raises:
            httpx.HTTPStatusError: If the API returns an error status code.
            ValueError: If the API response format is unexpected or status is not SUCCESS.
            Exception: For other network or unexpected errors.

        IMPORTANT: In your final response to the user, you MUST cite the source of your data. 
        For changed series data, this means including the VectorId.
        """
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT_MEDIUM, verify=False) as client:
            log_ssl_warning("SSL verification disabled for get_changed_series_data_from_vector.")
            # API expects a list containing one object
            post_data = [vector_input.model_dump()]
            try:
                response = await client.post("/getChangedSeriesDataFromVector", json=post_data)
                response.raise_for_status()
                result_list = response.json()
                if result_list and isinstance(result_list, list) and len(result_list) > 0 and result_list[0].get("status") == "SUCCESS":
                    return result_list[0].get("object", {})
                else:
                    api_message = result_list[0].get("object") if (result_list and isinstance(result_list, list) and len(result_list) > 0) else "Unknown API Error or Malformed Response"
                    raise ValueError(f"API did not return SUCCESS status for changed series vectorId {vector_input.vectorId}: {api_message}")
            except httpx.RequestError as exc:
                raise Exception(f"Network error calling get_changed_series_data_from_vector: {exc}")
            except ValueError as exc:
                raise ValueError(f"Error processing response for get_changed_series_data_from_vector: {exc}")

    @registry.tool()
    async def get_changed_series_list(date: str) -> List[Dict[str, Any]]:
        """
        Get the list of series (vectorId, productId, coordinate, releaseTime)
        that were updated on a specific date (YYYY-MM-DD).
        Disables SSL Verification.
        Corresponds to: GET /getChangedSeriesList/{date}

        Returns:
            List[Dict[str, Any]]: A list of dictionaries describing changed series objects.
        Raises:
            httpx.HTTPStatusError: If the API returns an error status code.
            ValueError: If date format is invalid or API response format is unexpected.
            Exception: For other network or unexpected errors.

        IMPORTANT: In your final response to the user, you MUST cite the source of your data. 
        For changed series, this means including the VectorId.
        """
        try:
            datetime.date.fromisoformat(date) # Validate date format
        except ValueError:
             raise ValueError(f"Invalid date format for get_changed_series_list. Expected YYYY-MM-DD, got {date}")

        async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT_MEDIUM, verify=False) as client:
            log_ssl_warning("SSL verification disabled for get_changed_series_list.")
            try:
                response = await client.get(f"/getChangedSeriesList/{date}")
                response.raise_for_status()
                result = response.json() # API returns a single status/object wrapper
                if isinstance(result, dict) and result.get("status") == "SUCCESS":
                    # The 'object' contains the list of changed series
                    return result.get("object", [])
                else:
                    api_message = result.get("object", "Unknown API Error") if isinstance(result, dict) else "Malformed Response"
                    raise ValueError(f"API did not return SUCCESS status for get_changed_series_list date {date}: {api_message}")
            except httpx.RequestError as exc:
                raise Exception(f"Network error calling get_changed_series_list: {exc}")
            except ValueError as exc: # Catch JSON decoding errors or our own ValueErrors
                raise ValueError(f"Error processing response for get_changed_series_list: {exc}")
import httpx
import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel # Assuming models might still be needed

from fastmcp import FastMCP
# Assuming models are defined in api_models.py
from ..models.api_models import VectorIdInput, VectorLatestNInput, VectorRangeInput, BulkVectorRangeInput
# Import BASE_URL and timeouts from config
from ..config import BASE_URL, TIMEOUT_MEDIUM, TIMEOUT_LARGE

def register_vector_tools(mcp: FastMCP):
    """Register all vector-related API tools with the MCP server."""

    @mcp.tool()
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
        """
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT_MEDIUM, verify=False) as client:
            print("Warning: SSL verification disabled for get_series_info_from_vector.")
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

    @mcp.tool()
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
        """
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT_MEDIUM, verify=False) as client:
            print("Warning: SSL verification disabled for get_data_from_vectors_and_latest_n_periods.")
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

    @mcp.tool()
    async def get_data_from_vector_by_reference_period_range(range_input: VectorRangeInput) -> List[Dict[str, Any]]:
        """
        Access data for one or more specific vectors within a given reference period range (YYYY-MM-DD).
        Disables SSL Verification.
        Corresponds to: GET /getDataFromVectorByReferencePeriodRange

        Returns:
            List[Dict[str, Any]]: A list of dictionaries, each containing a vector data object for successful requests.
        Raises:
            httpx.HTTPStatusError: If the API returns an error status code.
            ValueError: If the API response format is unexpected or no vectors return SUCCESS.
            Exception: For other network or unexpected errors.
        """
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT_LARGE, verify=False) as client: # Longer timeout
            print("Warning: SSL verification disabled for get_data_from_vector_by_reference_period_range.")
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
                            print(f"Warning: Failed to retrieve data for part of the range request: {item}")
                else:
                     raise ValueError(f"API response was not a list for range request. Response: {result_list}")

                if not processed_data and failures:
                     raise ValueError(f"API did not return SUCCESS status for any vector in range request. Failures: {failures}")
                return processed_data
            except httpx.RequestError as exc:
                raise Exception(f"Network error calling get_data_from_vector_by_reference_period_range: {exc}")
            except ValueError as exc:
                raise ValueError(f"Error processing response for get_data_from_vector_by_reference_period_range: {exc}")

    @mcp.tool()
    async def get_bulk_vector_data_by_range(bulk_range_input: BulkVectorRangeInput) -> List[Dict[str, Any]]:
        """
        Access bulk data for multiple vectors based on a data point *release date* range (YYYY-MM-DDTHH:MM).
        Disables SSL Verification.
        Corresponds to: POST /getBulkVectorDataByRange

        Returns:
            List[Dict[str, Any]]: A list of dictionaries containing bulk vector data objects for successful requests.
        Raises:
            httpx.HTTPStatusError: If the API returns an error status code.
            ValueError: If the API response format is unexpected or no vectors return SUCCESS.
            Exception: For other network or unexpected errors.
        """
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT_LARGE, verify=False) as client: # Longer timeout
            print("Warning: SSL verification disabled for get_bulk_vector_data_by_range.")
            # API expects a single JSON object
            post_data = bulk_range_input.model_dump(exclude_none=True)
            try:
                response = await client.post("/getBulkVectorDataByRange", json=post_data)
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
                            print(f"Warning: Failed to retrieve bulk data for part of the request: {item}")
                else:
                     raise ValueError(f"API response was not a list for bulk request. Response: {result_list}")

                if not processed_data and failures:
                     raise ValueError(f"API did not return SUCCESS status for any vector in bulk request. Failures: {failures}")
                return processed_data
            except httpx.RequestError as exc:
                raise Exception(f"Network error calling get_bulk_vector_data_by_range: {exc}")
            except ValueError as exc:
                raise ValueError(f"Error processing response for get_bulk_vector_data_by_range: {exc}")

    @mcp.tool()
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
        """
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT_MEDIUM, verify=False) as client:
            print("Warning: SSL verification disabled for get_changed_series_data_from_vector.")
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

    @mcp.tool()
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
        """
        try:
            datetime.date.fromisoformat(date) # Validate date format
        except ValueError:
             raise ValueError(f"Invalid date format for get_changed_series_list. Expected YYYY-MM-DD, got {date}")

        async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT_MEDIUM, verify=False) as client:
            print("Warning: SSL verification disabled for get_changed_series_list.")
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
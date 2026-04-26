"""Cube discovery tools — search and list cubes."""

import time
from typing import Dict, Any, List, Union

import httpx

from ...config import BASE_URL, TIMEOUT_LARGE, VERIFY_SSL
from ...models.api_models import CubeListInput, CubeSearchInput
from ...util.cache import get_cached_cubes_list_lite
from ...util.logger import log_ssl_warning, log_search_progress, log_data_validation_warning
from ...util.registry import ToolRegistry
from ...util.truncation import truncate_response


def register_cube_discovery_tools(registry: ToolRegistry):
    """Register cube discovery tools."""

    async def _fetch_all_cubes_list_lite_raw() -> List[Dict[str, Any]]:
        """Raw API fetch for cache use — returns full unpaginated list."""
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT_LARGE, verify=VERIFY_SSL) as client:
            response = await client.get("/getAllCubesListLite")
            response.raise_for_status()
            return response.json()

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
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT_LARGE, verify=VERIFY_SSL) as client:
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
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT_LARGE, verify=VERIFY_SSL) as client:
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
            all_cubes_lite = await get_cached_cubes_list_lite(_fetch_all_cubes_list_lite_raw)

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


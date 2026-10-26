"""Cube discovery tools — search and list cubes."""

import re
import time
from typing import Dict, Any, List, Union

import httpx

from ...config import BASE_URL, TIMEOUT_LARGE, VERIFY_SSL
from ...models.api_models import CubeListInput, CubeSearchInput
from ...util.cache import get_cached_cubes_list_lite
from ...util.logger import log_ssl_warning, log_search_progress, log_data_validation_warning
from ...util.registry import READ_ONLY, ToolRegistry
from ...util.truncation import truncate_response


_SEARCH_FIELDS = ("productId", "cubeTitleEn", "cubeStartDate", "cubeEndDate", "frequencyCode", "releaseTime")
_DATE_FIELDS = ("cubeStartDate", "cubeEndDate", "releaseTime")
# Search results that also get the table's SDMX key layout, so the agent can often skip get_sdmx_structure
_KEY_TEMPLATE_HITS = 3


def _cache_cube(cube: Dict[str, Any]) -> Dict[str, Any]:
    """What search keeps from getAllCubesList: titles, dates, status and dimension names.
    About 3 MB for the whole catalogue, versus 23 MB for the parsed full list."""
    kept = {k: cube.get(k) for k in (*_SEARCH_FIELDS, "cubeTitleFr", "archived")}
    dims = sorted(cube.get("dimensions") or [], key=lambda d: d.get("dimensionPositionId", 0))
    # Same normalization as SDMX dimension ids (e.g. "Products and product groups" ->
    # "Products_and_product_groups"), so the template matches key-error messages
    kept["key_template"] = ".".join(re.sub(r"[^0-9A-Za-z_]", "_", d.get("dimensionNameEn", "")) for d in dims)
    return kept


def _slim_cube(cube: Dict[str, Any], with_key_template: bool = False) -> Dict[str, Any]:
    """Search result fields: enough to pick a table; get_cube_metadata has the rest."""
    slim = {k: cube.get(k) for k in _SEARCH_FIELDS}
    for k in _DATE_FIELDS:
        if isinstance(slim[k], str):
            slim[k] = slim[k][:10]  # YYYY-MM-DD; the time of day doesn't help pick a table
    slim["archived"] = cube.get("archived") == "1"  # WDS: "1" = archived, "2" = current
    if with_key_template and cube.get("key_template"):
        slim["key_template"] = cube["key_template"]
    return slim


def register_cube_discovery_tools(registry: ToolRegistry):
    """Register cube discovery tools."""

    async def _fetch_search_catalogue() -> List[Dict[str, Any]]:
        """Catalogue for the search cache. getAllCubesList rather than the lite list
        for its dimension names (key_template); about 1.3 MB gzipped vs 0.9 MB."""
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT_LARGE, verify=VERIFY_SSL) as client:
            response = await client.get("/getAllCubesList")
            response.raise_for_status()
            return [_cache_cube(c) for c in response.json()]

    @registry.tool(annotations=READ_ONLY)
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

    @registry.tool(annotations=READ_ONLY)
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

    @registry.tool(annotations=READ_ONLY)
    async def search_cubes_by_title(search_input: CubeSearchInput) -> Dict[str, Any]:
        """
        Searches for data cubes/tables where the English or French title contains
        the provided search term (case-insensitive).

        Multiple keywords use AND logic (e.g., "tobacco smoking age" finds cubes
        containing ALL three words). Returns max_results matches (default 10) from offset.

        Returns {"data": [...], "total_matches": N, "showing": M, ?"next_offset"}. Each
        result has productId, cubeTitleEn, cubeStartDate, cubeEndDate, frequencyCode,
        releaseTime and archived (true = discontinued table); current tables come first.
        The top 3 also have key_template: the table's SDMX dimensions in key order
        (e.g. "Geography.Products_and_product_groups"), one key position each.

        IMPORTANT: In your final response to the user, you MUST cite the source of your data.
        For cubes, this means including the ProductId (pid) and the Title.
        """
        start_time = time.time()
        search_term = search_input.search_term
        max_results = search_input.max_results
        offset = max(search_input.offset, 0)
        log_search_progress(f"Searching for cubes with title containing: '{search_term}'")

        catalogue = await get_cached_cubes_list_lite(_fetch_search_catalogue)

        search_terms = search_term.lower().split()
        matching_cubes = []
        for cube in catalogue:
            title_en = (cube.get("cubeTitleEn", "") or "").lower()
            title_fr = (cube.get("cubeTitleFr", "") or "").lower()

            match_en = all(term in title_en for term in search_terms)
            match_fr = all(term in title_fr for term in search_terms)

            if match_en or match_fr:
                matching_cubes.append(cube)

        # Current tables before archived ones; stable sort keeps catalogue order within each
        matching_cubes.sort(key=lambda c: c.get("archived") == "1")

        elapsed = time.time() - start_time
        total_found = len(matching_cubes)
        log_search_progress(f"Found {total_found} cubes matching keywords '{search_terms}' in {elapsed:.2f}s")

        page = matching_cubes[offset:offset + max_results]
        result: Dict[str, Any] = {
            "data": [
                _slim_cube(c, with_key_template=offset + i < _KEY_TEMPLATE_HITS) for i, c in enumerate(page)
            ],
            "total_matches": total_found,
            "showing": len(page),
        }
        if offset + len(page) < total_found:
            result["next_offset"] = offset + len(page)
            result["message"] = (
                f"Showing {offset + 1}-{offset + len(page)} of {total_found} matches. "
                "Adding a keyword usually beats paging; otherwise pass offset=next_offset."
            )
        return result

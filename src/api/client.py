import asyncio
import httpx
from typing import Dict, List, Any, Optional, Union
import json
from ..config import BASE_URL, TIMEOUT_SMALL, TIMEOUT_MEDIUM, TIMEOUT_LARGE, VERIFY_SSL
from ..util.logger import log_ssl_warning

_RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})
_MAX_RETRY_ATTEMPTS = 3


async def make_get_request(endpoint: str, params: Optional[Dict[str, Any]] = None,
                           timeout: float = TIMEOUT_SMALL) -> Any:
    """Make a GET request to the StatCan WDS API with retry on 5xx/429."""
    if not VERIFY_SSL:
        log_ssl_warning(f"SSL verification disabled for {endpoint}.")
    for attempt in range(_MAX_RETRY_ATTEMPTS):
        try:
            async with httpx.AsyncClient(base_url=BASE_URL, timeout=timeout, verify=VERIFY_SSL) as client:
                response = await client.get(endpoint, params=params)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code not in _RETRY_STATUSES or attempt == _MAX_RETRY_ATTEMPTS - 1:
                raise
            await asyncio.sleep(min(1.0 * (2 ** attempt), 10.0))


async def make_post_request(endpoint: str, data: Union[List[Dict[str, Any]], Dict[str, Any]],
                            timeout: float = TIMEOUT_SMALL) -> Any:
    """Make a POST request to the StatCan WDS API with retry on 5xx/429."""
    if not VERIFY_SSL:
        log_ssl_warning(f"SSL verification disabled for {endpoint}.")
    for attempt in range(_MAX_RETRY_ATTEMPTS):
        try:
            async with httpx.AsyncClient(base_url=BASE_URL, timeout=timeout, verify=VERIFY_SSL) as client:
                response = await client.post(endpoint, json=data)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code not in _RETRY_STATUSES or attempt == _MAX_RETRY_ATTEMPTS - 1:
                raise
            await asyncio.sleep(min(1.0 * (2 ** attempt), 10.0))


async def make_sdmx_get(
    url: str,
    *,
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    timeout: float = TIMEOUT_MEDIUM,
) -> httpx.Response:
    """GET request to an SDMX endpoint with retry on 5xx/429. Returns raw response."""
    if not VERIFY_SSL:
        log_ssl_warning(f"SSL verification disabled for {url}.")
    for attempt in range(_MAX_RETRY_ATTEMPTS):
        try:
            async with httpx.AsyncClient(timeout=timeout, verify=VERIFY_SSL) as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                return response
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code not in _RETRY_STATUSES or attempt == _MAX_RETRY_ATTEMPTS - 1:
                raise
            await asyncio.sleep(min(1.0 * (2 ** attempt), 10.0))

def extract_success_object(result_list: List[Dict[str, Any]], index: int = 0) -> Dict[str, Any]:
    """Extract the 'object' from a successful API response."""
    if result_list and isinstance(result_list, list) and len(result_list) > index:
        if result_list[index].get("status") == "SUCCESS":
            return result_list[index].get("object", {})
        else:
            api_message = result_list[index].get("object", "Unknown API Error")
            raise ValueError(f"API did not return SUCCESS status: {api_message}")
    else:
        raise ValueError("Unexpected API response format.")
import httpx
from typing import Dict, List, Any, Optional, Union
import json
from ..config import BASE_URL, TIMEOUT_SMALL, TIMEOUT_MEDIUM, TIMEOUT_LARGE, VERIFY_SSL
from ..util.logger import log_ssl_warning

async def make_get_request(endpoint: str, params: Optional[Dict[str, Any]] = None, 
                         timeout: float = TIMEOUT_SMALL) -> Any:
    """Make a GET request to the StatCan API."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=timeout, verify=VERIFY_SSL) as client:
        if not VERIFY_SSL:
            log_ssl_warning(f"SSL verification disabled for {endpoint}.")
        response = await client.get(endpoint, params=params)
        response.raise_for_status()
        return response.json()

async def make_post_request(endpoint: str, data: Union[List[Dict[str, Any]], Dict[str, Any]], 
                         timeout: float = TIMEOUT_SMALL) -> Any:
    """Make a POST request to the StatCan API."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=timeout, verify=VERIFY_SSL) as client:
        if not VERIFY_SSL:
            log_ssl_warning(f"SSL verification disabled for {endpoint}.")
        response = await client.post(endpoint, json=data)
        response.raise_for_status()
        return response.json()

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
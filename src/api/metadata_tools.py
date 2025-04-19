from fastmcp import FastMCP
from typing import Dict, Any
from .client import make_get_request, extract_success_object

def register_metadata_tools(mcp: FastMCP):
    """Register metadata-related API tools with the MCP server."""
    
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
        result = await make_get_request("/getCodeSets")
        if result.get("status") == "SUCCESS":
            # The 'object' contains the dictionary of code sets
            return result.get("object", {})
        else:
            api_message = result.get("object", "Unknown API Error")
            raise ValueError(f"API did not return SUCCESS status: {api_message}")

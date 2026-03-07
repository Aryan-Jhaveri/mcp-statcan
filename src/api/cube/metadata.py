    # --- Metadata Tools ---
    @registry.tool()
    async def get_cube_metadata(metadata_input: CubeMetadataInput) -> Dict[str, Any]:
        """
        Retrieves detailed metadata for a specific data table/cube using its ProductId.
        Includes dimension info, titles, date ranges, codes, etc. Disables SSL Verification.
        Corresponds to: POST /getCubeMetadata

        Start with summary=True (default). The summary strips noise (French translations,
        archive codes, footnotes) and shows only 3 sample members per dimension with
        _next_steps guidance. Safe for all context window sizes.
        Set summary=False only if you need the full raw member list or all API fields.

        To browse dimension codes for get_sdmx_data key construction, use get_sdmx_structure.
        To resolve a coordinate to a vectorId, use get_series_info.

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

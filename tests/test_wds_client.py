"""
Tests for the WDS API client.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from src.wds_client import WDSClient

@pytest.fixture
def wds_client():
    """Create a WDS client for testing."""
    return WDSClient()

@pytest.mark.asyncio
async def test_get_changed_cube_list(wds_client):
    """Test getting changed cube list."""
    with patch.object(wds_client, '_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {
            "status": "SUCCESS",
            "object": [
                {
                    "productId": "12345",
                    "cubeTitleEn": "Test Dataset",
                    "releaseTime": "2023-01-01",
                }
            ]
        }
        
        result = await wds_client.get_changed_cube_list(1)
        
        mock_request.assert_called_once()
        assert result["status"] == "SUCCESS"
        assert len(result["object"]) == 1
        assert result["object"][0]["productId"] == "12345"

@pytest.mark.asyncio
async def test_get_cube_metadata(wds_client):
    """Test getting cube metadata."""
    with patch.object(wds_client, '_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {
            "status": "SUCCESS",
            "object": {
                "productId": "12345",
                "cubeTitleEn": "Test Dataset",
                "dimension": [
                    {"dimensionNameEn": "Geography"},
                    {"dimensionNameEn": "Time"},
                ]
            }
        }
        
        result = await wds_client.get_cube_metadata("12345")
        
        mock_request.assert_called_once()
        assert result["status"] == "SUCCESS"
        assert result["object"]["productId"] == "12345"
        assert len(result["object"]["dimension"]) == 2
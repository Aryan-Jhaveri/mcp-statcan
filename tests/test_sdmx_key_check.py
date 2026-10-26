"""Tests for SDMX key validation against the DSD (#137)."""

import asyncio

import httpx
import pytest
import respx
from httpx import Response

from src.api.sdmx.sdmx_tools import fetch_sdmx_rows
from src.config import SDMX_BASE_URL
from src.util.sdmx_xml import check_sdmx_key, parse_dsd_labels
from tests.sdmx_fixtures import DSD_XML, STRUCTURE_URL, mock_sdmx

DSD = parse_dsd_labels(DSD_XML)


@pytest.mark.parametrize("key", ["1.1", "1+2.1", ".", ".1", "2."])
def test_valid_keys_pass(key):
    assert check_sdmx_key(key, DSD, 18100004) is None


@pytest.mark.parametrize("key, positions", [("1", 1), ("1.1.1", 3)])
def test_wrong_position_count_names_the_dimensions(key, positions):
    msg = check_sdmx_key(key, DSD, 18100004)
    assert f"has {positions} position(s); table 18100004 has 2: Geography.Products" in msg
    assert "'1.'" in msg


def test_unknown_code_names_position_and_valid_codes():
    msg = check_sdmx_key("1+99.1", DSD, 18100004)
    assert "'99' at position 1 (Geography)" in msg
    assert "2 valid codes" in msg
    assert "1 (Canada)" in msg and "2 (Ontario)" in msg


def test_unknown_code_in_later_position():
    assert "at position 2 (Products)" in check_sdmx_key("1.7", DSD, 18100004)


@pytest.mark.asyncio
@respx.mock
async def test_bad_key_skips_the_data_request():
    respx.get(STRUCTURE_URL).mock(return_value=Response(200, text=DSD_XML))
    data = respx.get(f"{SDMX_BASE_URL}data/DF_18100004/99.1").mock(
        side_effect=lambda request: asyncio.sleep(60)  # StatCan hangs on an unknown first code
    )

    with pytest.raises(ValueError, match="Unknown code"):
        await asyncio.wait_for(fetch_sdmx_rows(18100004, "99.1"), timeout=5)
    assert not data.calls or data.calls.last.response is None


@pytest.mark.asyncio
@respx.mock
async def test_rejection_of_valid_key_explains_period_format():
    mock_sdmx(url=f"{SDMX_BASE_URL}data/DF_18100004/1.1", status=406, data_xml='{"message":"x"}')

    with pytest.raises(httpx.HTTPStatusError, match="check the period format") as exc_info:
        await fetch_sdmx_rows(18100004, "1.1", start_period="2024-13")
    assert exc_info.value.response.status_code == 406  # CLI exit codes still branch on status

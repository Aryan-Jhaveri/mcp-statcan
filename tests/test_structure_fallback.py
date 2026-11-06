"""Labels from WDS metadata when StatCan's SDMX structure stays truncated (#175)."""

import asyncio

import httpx
import pytest
import respx
from httpx import Response
from mcp import Client

from src import config
from src.api import metadata_tools
from src.api.sdmx import sdmx_tools
from src.api.sdmx.sdmx_tools import STRUCTURE_FALLBACK_NOTE, fetch_sdmx_rows, fetch_structure_xml
from src.api.sdmx.wds_fallback import build_structure_xml, is_fallback_structure
from src.server import create_server, registry
from src.util.sdmx_xml import align_dimension_ids, parse_dsd_labels
from tests.sdmx_fixtures import DATA_URL, DSD_XML, STRUCTURE_URL, make_data_xml

TRUNCATED = DSD_XML[: len(DSD_XML) // 2]
METADATA_URL = f"{config.BASE_URL}/getCubeMetadata"
CODE_SETS_URL = f"{config.BASE_URL}/getCodeSets"

CUBE = {
    "productId": 18100004,
    "cubeTitleEn": "Consumer Price Index",
    "dimension": [
        {
            "dimensionPositionId": 1,
            "dimensionNameEn": "Geography",
            "member": [
                {"memberId": 1, "memberNameEn": "Canada", "parentMemberId": None},
                {"memberId": 2, "memberNameEn": "Ontario", "parentMemberId": 1},
            ],
        },
        {
            "dimensionPositionId": 2,
            "dimensionNameEn": "Products",
            "member": [{"memberId": 1, "memberNameEn": "All-items", "parentMemberId": None}],
        },
    ],
}
CODE_SETS = {
    "uom": [{"memberUomCode": 17, "memberUomEn": "2002=100"}],
    "scalar": [{"scalarFactorCode": 0, "scalarFactorDescEn": "units"}],
    "symbol": [
        {"symbolCode": "0", "symbolRepresentationEn": None, "symbolDescEn": "none"},
        {"symbolCode": "1", "symbolRepresentationEn": "p", "symbolDescEn": "preliminary"},
    ],
    "status": [{"statusCode": "1", "statusRepresentationEn": "..", "statusDescEn": "not available"}],
    "securityLevel": [{"securityLevelCode": 0, "securityLevelRepresentationEn": None, "securityLevelDescEn": "public"}],
    "terminated": [{"codeId": 1, "displayCodeEn": "t", "codeTextEn": "terminated"}],
}


@pytest.fixture(autouse=True)
def no_sleep_and_fresh_code_sets(monkeypatch):
    async def _instant(_seconds):
        return None

    monkeypatch.setattr(asyncio, "sleep", _instant)
    monkeypatch.setattr(metadata_tools, "_code_sets_cache", None)


def _mock_truncated_dsd_and_wds(cube=CUBE):
    dsd = respx.get(STRUCTURE_URL).mock(return_value=Response(200, text=TRUNCATED))
    meta = respx.post(METADATA_URL).mock(
        return_value=Response(200, json=[{"status": "SUCCESS", "object": cube}])
    )
    respx.get(CODE_SETS_URL).mock(return_value=Response(200, json={"status": "SUCCESS", "object": CODE_SETS}))
    return dsd, meta


def test_built_structure_labels_match_statcan_dsd_format():
    xml = build_structure_xml(18100004, CUBE, CODE_SETS)
    assert is_fallback_structure(xml)
    labels = parse_dsd_labels(xml)
    assert labels["dimensions"] == ["Geography", "Products"]
    assert labels["labels"]["Geography"] == {"1": "Canada", "2": "Ontario"}
    assert labels["labels"]["UOM"] == {"17": "2002=100"}
    # Same wording as StatCan's DSDs: '<symbol> = <description>', code when no symbol
    assert labels["labels"]["SYMBOL"] == {"0": "0 = none", "1": "p = preliminary"}
    assert labels["labels"]["STATUS_CAN"] == {"1": ".. = not available"}
    assert labels["labels"]["TERMINATED"] == {"1": "t = terminated"}

    parsed = sdmx_tools._parse_structure_xml(xml, 18100004, member_limit=None)
    assert parsed["name"] == "Data Structure of Consumer Price Index"
    geo = parsed["dimensions"][0]
    assert (geo["id"], geo["position"]) == ("Geography", 1)
    assert geo["codes"] == [{"id": "1", "name": "Canada"}, {"id": "2", "name": "Ontario", "parent": "1"}]


@respx.mock
@pytest.mark.asyncio
async def test_truncated_dsd_falls_back_to_wds_labels():
    _mock_truncated_dsd_and_wds()
    respx.get(DATA_URL).mock(return_value=Response(200, text=make_data_xml()))
    rows, _ = await fetch_sdmx_rows(18100004, "1+2.1")
    assert {r["Geography"] for r in rows} == {"Canada", "Ontario"}
    assert rows[0]["Products"] == "All-items"
    assert rows[0]["UOM"] == "2002=100"
    assert rows[0]["_series_key"] == "1.1"
    assert sdmx_tools.used_structure_fallback()


@respx.mock
@pytest.mark.asyncio
async def test_key_check_still_works_with_fallback_structure():
    _mock_truncated_dsd_and_wds()
    respx.get(f"{config.SDMX_BASE_URL}data/DF_18100004/9.1").mock(return_value=Response(200, text=make_data_xml()))
    with pytest.raises(ValueError, match="Unknown code"):
        await fetch_sdmx_rows(18100004, "9.1")


@respx.mock
@pytest.mark.asyncio
async def test_fallback_is_cached_briefly_then_real_dsd_retried():
    dsd, meta = _mock_truncated_dsd_and_wds()
    await fetch_structure_xml(18100004)
    await fetch_structure_xml(18100004)
    assert dsd.call_count == config.SDMX_STRUCTURE_ATTEMPTS  # second call used the fallback cache
    assert meta.call_count == 1
    assert 18100004 not in sdmx_tools._structure_cache  # never stored as the real DSD

    # Past the short TTL, the real DSD is tried again; StatCan has fixed it by now
    built_at, text = sdmx_tools._fallback_structure_cache[18100004]
    sdmx_tools._fallback_structure_cache[18100004] = (built_at - config.SDMX_STRUCTURE_FALLBACK_TTL - 1, text)
    dsd.mock(return_value=Response(200, text=DSD_XML))
    assert await fetch_structure_xml(18100004) == DSD_XML
    assert config.SDMX_STRUCTURE_FALLBACK_TTL < config.SDMX_STRUCTURE_CACHE_TTL


@respx.mock
@pytest.mark.asyncio
async def test_stalled_dsd_also_falls_back():
    respx.get(STRUCTURE_URL).mock(side_effect=httpx.ReadTimeout("stalled"))
    respx.post(METADATA_URL).mock(return_value=Response(200, json=[{"status": "SUCCESS", "object": CUBE}]))
    respx.get(CODE_SETS_URL).mock(return_value=Response(200, json={"status": "SUCCESS", "object": CODE_SETS}))
    assert is_fallback_structure(await fetch_structure_xml(18100004))


def test_align_dimension_ids_renames_by_position():
    # WDS calls position 2 'Products and product groups'; the data message says 'Products'
    cube = {**CUBE, "dimension": [CUBE["dimension"][0], {**CUBE["dimension"][1], "dimensionNameEn": "Products and product groups"}]}
    dsd = parse_dsd_labels(build_structure_xml(18100004, cube, CODE_SETS))
    assert dsd["dimensions"] == ["Geography", "Products_and_product_groups"]
    aligned = align_dimension_ids(dsd, make_data_xml())
    assert aligned["dimensions"] == ["Geography", "Products"]
    assert aligned["labels"]["Products"] == {"1": "All-items"}


@respx.mock
@pytest.mark.asyncio
async def test_core_get_sdmx_data_says_labels_came_from_wds():
    _mock_truncated_dsd_and_wds()
    respx.get(f"{config.SDMX_BASE_URL}data/DF_18100004/1.1").mock(return_value=Response(200, text=make_data_xml()))
    registry._tools.clear()
    registry._handlers.clear()
    server = create_server(http_mode=True, toolset="core")
    try:
        async with Client(server) as client:
            result = await client.call_tool("get_sdmx_data", {"productId": 18100004, "key": "1.1", "full": True})
            structure = await client.call_tool("get_sdmx_structure", {"productId": 18100004})
    finally:
        registry._tools.clear()
        registry._handlers.clear()
    assert not result.is_error, result.content[0].text
    assert STRUCTURE_FALLBACK_NOTE in result.structured_content["_message"]
    assert not structure.is_error
    assert STRUCTURE_FALLBACK_NOTE in structure.structured_content["_message"]


@respx.mock
@pytest.mark.asyncio
async def test_good_dsd_adds_no_note():
    respx.get(STRUCTURE_URL).mock(return_value=Response(200, text=DSD_XML))
    respx.get(DATA_URL).mock(return_value=Response(200, text=make_data_xml()))
    await fetch_sdmx_rows(18100004, "1+2.1")
    assert not sdmx_tools.used_structure_fallback()
    assert sdmx_tools.with_fallback_note({"_sdmx_url": "x"}) == {"_sdmx_url": "x"}

"""SDMX tools' structuredContent must validate against their published outputSchema.

Runs each tool through the SDK's in-memory Client (which validates structuredContent
against outputSchema and raises on mismatch) with StatCan responses mocked by respx.
"""

import pytest
import respx
from httpx import Response
from mcp import Client

from src import config
from src.config import SDMX_BASE_URL
from src.server import create_server, registry
from tests.sdmx_fixtures import DATA_URL, N_PERIODS, make_data_xml, mock_sdmx

STRUCTURE_URL = f"{SDMX_BASE_URL}structure/Data_Structure_18100004"


def _structure_xml(n_products: int = 12) -> str:
    """Minimal SDMX 2.1 structure: Geography (with a parent ref) + a large Products codelist."""
    products = "".join(
        f'<str:Code id="{i}"><com:Name xml:lang="en">Product {i}</com:Name>'
        + (f'<str:Parent><Ref id="1"/></str:Parent>' if i > 1 else "")
        + "</str:Code>"
        for i in range(1, n_products + 1)
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<mes:Structure xmlns:mes="http://www.sdmx.org/resources/sdmxml/schemas/v2_1/message"
               xmlns:str="http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure"
               xmlns:com="http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common">
 <mes:Structures>
  <str:Codelists>
   <str:Codelist id="CL_Geography"><com:Name xml:lang="en">Geography</com:Name>
    <str:Code id="1"><com:Name xml:lang="en">Canada</com:Name></str:Code>
    <str:Code id="2"><com:Name xml:lang="en">Ontario</com:Name><str:Parent><Ref id="1"/></str:Parent></str:Code>
   </str:Codelist>
   <str:Codelist id="CL_Products"><com:Name xml:lang="en">Products</com:Name>{products}</str:Codelist>
  </str:Codelists>
  <str:DataStructures>
   <str:DataStructure id="Data_Structure_18100004"><com:Name xml:lang="en">Consumer Price Index</com:Name>
    <str:DataStructureComponents><str:DimensionList>
     <str:Dimension id="Geography" position="1"><str:LocalRepresentation><str:Enumeration><Ref id="CL_Geography"/></str:Enumeration></str:LocalRepresentation></str:Dimension>
     <str:Dimension id="Products" position="2"><str:LocalRepresentation><str:Enumeration><Ref id="CL_Products"/></str:Enumeration></str:LocalRepresentation></str:Dimension>
     <str:TimeDimension id="TIME_PERIOD" position="3"/>
    </str:DimensionList></str:DataStructureComponents>
   </str:DataStructure>
  </str:DataStructures>
 </mes:Structures>
</mes:Structure>"""


def _fresh_server(http_mode: bool):
    registry._tools.clear()
    registry._handlers.clear()
    return create_server(http_mode=http_mode)


async def _call(server, name, args):
    async with Client(server) as client:
        tools = {t.name: t for t in (await client.list_tools()).tools}
        assert tools[name].output_schema is not None, f"{name} has no outputSchema"
        result = await client.call_tool(name, args)  # raises if structuredContent mismatches
    assert result.is_error is False, result.content[0].text
    return tools[name], result.structured_content


@pytest.mark.asyncio
@respx.mock
async def test_rows_tools():
    mock_sdmx(make_data_xml(first_value="0.0"))
    meta, sc = await _call(_fresh_server(True), "get_sdmx_data", {"productId": 18100004, "key": "1+2.1"})
    assert sc["row_count"] == 2 * N_PERIODS
    assert sc["_truncated"] is True
    assert meta.annotations.read_only_hint is True
    canada = sc["series"][0]
    assert {k: v for k, v in canada.items() if k != "observations"} == {
        "Geography": "Canada", "Products": "All-items", "_series_key": "1.1", "VECTOR_ID": "41690973", "UOM": "2002=100",
    }
    assert canada["observations"][:2] == [["1700", 0.0], ["1701", 1.0]]


@pytest.mark.asyncio
@respx.mock
async def test_rows_keep_observation_attributes_and_nulls():
    mock_sdmx(make_data_xml(first_value=None, obs_attr_on=(0, 1)))
    _, sc = await _call(_fresh_server(True), "get_sdmx_data", {"productId": 18100004, "key": "1+2.1"})
    obs = sc["series"][0]["observations"]
    assert obs[0] == ["1700", None]
    assert obs[1] == ["1701", 1.0, {"STATUS_CAN": ".. = not available"}]
    assert "STATUS_CAN" not in sc["series"][0]


@pytest.mark.asyncio
@respx.mock
async def test_vector_data():
    mock_sdmx(make_data_xml(first_value="0.0"), url=f"{SDMX_BASE_URL}vector/v41690973")
    _, sc = await _call(_fresh_server(True), "get_sdmx_vector_data", {"vectorId": 41690973, "lastNObservations": 5})
    assert sc["_sdmx_url"].startswith(f"{SDMX_BASE_URL}vector/v41690973")


@pytest.mark.asyncio
@respx.mock
async def test_query_sdmx():
    mock_sdmx(make_data_xml(first_value="0.0"))
    _, sc = await _call(
        _fresh_server(True), "query_sdmx",
        {"productId": 18100004, "key": "1+2.1", "sql": 'SELECT "Geography", COUNT(*) AS n FROM data GROUP BY 1'},
    )
    assert sc["rows"] == [{"Geography": "Canada", "n": N_PERIODS}, {"Geography": "Ontario", "n": N_PERIODS}]


@pytest.mark.asyncio
@respx.mock
async def test_query_sdmx_sql_error_is_tool_error():
    mock_sdmx(make_data_xml())
    async with Client(_fresh_server(True)) as client:
        await client.list_tools()
        result = await client.call_tool("query_sdmx", {"productId": 18100004, "key": "1+2.1", "sql": "SELECT nope FROM data"})
    assert result.is_error is True
    assert "table_columns" in result.content[0].text


@pytest.mark.asyncio
@respx.mock
async def test_structure():
    respx.get(STRUCTURE_URL).mock(return_value=Response(200, text=_structure_xml()))
    _, sc = await _call(_fresh_server(True), "get_sdmx_structure", {"productId": 18100004})
    geo, products = sc["dimensions"]
    assert geo["codes"][1] == {"id": "2", "name": "Ontario", "parent": "1"}
    # parentless first, then numeric (not string) order
    assert [c["id"] for c in products["codes"]] == [str(i) for i in range(1, 11)]
    assert products["_truncated"] is True and products["_code_count"] == 12


@pytest.mark.asyncio
@respx.mock
async def test_key_for_dimension():
    respx.get(STRUCTURE_URL).mock(return_value=Response(200, text=_structure_xml()))
    _, sc = await _call(_fresh_server(True), "get_sdmx_key_for_dimension", {"productId": 18100004, "dimension_position": 2})
    assert sc["leaf_count"] == 11  # code 1 is everyone's parent
    assert sc["or_key"].startswith("2+3+")


@pytest.mark.asyncio
@respx.mock
async def test_fetch_sdmx_to_database(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_FILE", str(tmp_path / "test.db"))
    mock_sdmx(make_data_xml(first_value="0.0"))
    meta, sc = await _call(
        _fresh_server(False), "fetch_sdmx_to_database",
        {"productId": 18100004, "key": "1+2.1", "table_name": "cpi"},
    )
    assert sc["rows_inserted"] == 2 * N_PERIODS
    assert meta.annotations.destructive_hint is True

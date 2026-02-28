"""SDMX REST API tools for Statistics Canada.

Provides server-side filtered data access via the SDMX REST API at:
  https://www150.statcan.gc.ca/t1/wds/sdmx/statcan/rest/

Three tools:
  get_sdmx_structure  — fetch Data Structure Definition (DSD) as JSON: dimensions + codelists
  get_sdmx_data       — fetch filtered observations by productId + key
  get_sdmx_vector_data — fetch observations for a single vectorId
"""

import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

import httpx

from ..config import (
    MAX_SDMX_ROWS,
    SDMX_BASE_URL,
    SDMX_JSON_ACCEPT,
    SDMX_XML_ACCEPT,
    TIMEOUT_MEDIUM,
)
from ..models.sdmx_models import SDMXDataInput, SDMXStructureInput, SDMXVectorInput
from ..util.registry import ToolRegistry
from ..util.sdmx_json import flatten_sdmx_json
from ..util.truncation import DEFAULT_MEMBER_LIMIT

# SDMX 2.1 XML namespaces
_NS = {
    "mes": "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/message",
    "str": "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure",
    "com": "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common",
}
_XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"


def _get_english_name(element: ET.Element) -> str:
    """Return the English com:Name text, falling back to the first com:Name."""
    names = element.findall("com:Name", _NS)
    for name in names:
        if name.get(_XML_LANG) == "en":
            return (name.text or "").strip()
    if names:
        return (names[0].text or "").strip()
    return ""


def _find_ref_id(element: ET.Element) -> Optional[str]:
    """Return the id attribute of the first Ref child element (any namespace)."""
    for child in element:
        tag = child.tag
        if tag == "Ref" or tag.endswith("}Ref"):
            return child.get("id")
    return None


def _parse_structure_xml(xml_text: str, product_id: int) -> Dict[str, Any]:
    """Parse SDMX 2.1 Structure XML into a JSON-serialisable summary dict."""
    root = ET.fromstring(xml_text)

    # ── Collect all codelists ───────────────────────────────────────────────
    codelists: Dict[str, List[Dict[str, Any]]] = {}
    for cl in root.findall(".//str:Codelist", _NS):
        cl_id = cl.get("id", "")
        codes: List[Dict[str, Any]] = []
        for code in cl.findall("str:Code", _NS):
            entry: Dict[str, Any] = {
                "id": code.get("id", ""),
                "name": _get_english_name(code),
            }
            parent_el = code.find("str:Parent", _NS)
            if parent_el is not None:
                parent_id = _find_ref_id(parent_el)
                if parent_id:
                    entry["parent"] = parent_id
            codes.append(entry)
        codelists[cl_id] = codes

    # ── Locate the DataStructure element ───────────────────────────────────
    ds_name = ""
    dimensions: List[Dict[str, Any]] = []

    ds = root.find(f".//str:DataStructure[@id='Data_Structure_{product_id}']", _NS)
    if ds is not None:
        ds_name = _get_english_name(ds)

        dim_list = ds.find(".//str:DimensionList", _NS)
        if dim_list is not None:
            # str:Dimension only — skip str:TimeDimension (no codelist, drives obs axis)
            for dim in dim_list.findall("str:Dimension", _NS):
                dim_id = dim.get("id", "")
                pos = int(dim.get("position", "0"))

                enum_el = dim.find(".//str:Enumeration", _NS)
                cl_id = _find_ref_id(enum_el) if enum_el is not None else None

                codes_list = codelists.get(cl_id, []) if cl_id else []
                total = len(codes_list)
                truncated = total > DEFAULT_MEMBER_LIMIT

                dim_info: Dict[str, Any] = {
                    "id": dim_id,
                    "position": pos,
                    "codelist": cl_id,
                    "codes": codes_list[:DEFAULT_MEMBER_LIMIT] if truncated else codes_list,
                    "_code_count": total,
                    "_truncated": truncated,
                }
                if truncated:
                    dim_info["_message"] = (
                        f"Showing first {DEFAULT_MEMBER_LIMIT} of {total} codes. "
                        f"Use '+' for OR or omit for wildcard in key at position {pos}."
                    )
                dimensions.append(dim_info)

            dimensions.sort(key=lambda d: d["position"])

    return {"name": ds_name, "productId": product_id, "dimensions": dimensions}


def register_sdmx_tools(registry: ToolRegistry) -> None:
    """Register all SDMX REST API tools with the MCP server."""

    @registry.tool()
    async def get_sdmx_structure(structure_input: SDMXStructureInput) -> Dict[str, Any]:
        """
        Fetch the Data Structure Definition (DSD) for a StatCan table via SDMX REST.

        Returns dimension codelists with code IDs, names, and parent hierarchy.
        Use this BEFORE get_sdmx_data to understand the key syntax for that table.

        Each dimension entry includes:
          - id: dimension identifier (e.g. "Geography")
          - position: its slot in the dot-separated key string (1-based)
          - codelist: the SDMX codelist ID (e.g. "CL_Geography")
          - codes: list of {id, name, ?parent} — truncated to 10 for large codelists
          - _code_count / _truncated: total size and truncation flag

        Key construction rules:
          - "1.2.1"   = position-1 code 1, position-2 code 2, position-3 code 1
          - ".2.1"    = wildcard position 1 (all geographies), Gender=2, Age=1
          - "1+2.2.1" = Geography 1 or 2 (OR syntax)
          - WDS memberIds == SDMX codelist codes — no translation needed

        IMPORTANT: ALWAYS CITE _sdmx_url in your response.
        """
        product_id = structure_input.productId
        url = f"{SDMX_BASE_URL}structure/Data_Structure_{product_id}"

        async with httpx.AsyncClient(timeout=TIMEOUT_MEDIUM, verify=False) as client:
            response = await client.get(url, headers={"Accept": SDMX_XML_ACCEPT})
            response.raise_for_status()

        result = _parse_structure_xml(response.text, product_id)
        result["_sdmx_url"] = url
        return result

    @registry.tool()
    async def get_sdmx_data(data_input: SDMXDataInput) -> Dict[str, Any]:
        """
        Fetch filtered time-series observations from a StatCan table via SDMX REST.

        Filtering is done server-side — only the requested slice is returned.
        Call get_sdmx_structure first to see dimension positions and valid codes.

        Key syntax (dot-separated codes in dimension position order):
          "1.2.1"   = Geography=1 (Canada), Gender=2 (Men+), Age=1 (All ages)
          ".2.1"    = all geographies, Gender=2, Age=1  (wildcard)
          "1+2.2.1" = Geography 1 or 2, Gender=2, Age=1 (OR)

        Time filtering:
          lastNObservations=12  → last 12 periods (e.g. 1 year of monthly data)
          startPeriod="2020"    → from 2020 onwards (annual); "2020-01" for monthly
          endPeriod="2023-12"   → up to Dec 2023

        Output rows contain: dimension values, "period", "value", SCALAR_FACTOR,
        UOM, VECTOR_ID, STATUS, and other SDMX attributes.

        IMPORTANT: ALWAYS CITE _sdmx_url and productId/key in your response.
        """
        product_id = data_input.productId
        key = data_input.key
        url = f"{SDMX_BASE_URL}data/DF_{product_id}/{key}"

        params: Dict[str, Any] = {}
        if data_input.lastNObservations is not None:
            params["lastNObservations"] = data_input.lastNObservations
        if data_input.startPeriod:
            params["startPeriod"] = data_input.startPeriod
        if data_input.endPeriod:
            params["endPeriod"] = data_input.endPeriod

        async with httpx.AsyncClient(timeout=TIMEOUT_MEDIUM, verify=False) as client:
            response = await client.get(
                url, params=params, headers={"Accept": SDMX_JSON_ACCEPT}
            )
            response.raise_for_status()
            sdmx_url = str(response.url)
            rows = flatten_sdmx_json(response.json())

        result: Dict[str, Any] = {"_sdmx_url": sdmx_url, "row_count": len(rows)}
        if len(rows) > MAX_SDMX_ROWS:
            result["data"] = rows[:MAX_SDMX_ROWS]
            result["_truncated"] = True
            result["_message"] = (
                f"Response capped at {MAX_SDMX_ROWS} rows (total: {len(rows)}). "
                "Narrow your query with a more specific key, or use "
                "lastNObservations / startPeriod / endPeriod."
            )
        else:
            result["data"] = rows
            result["_truncated"] = False

        return result

    @registry.tool()
    async def get_sdmx_vector_data(vector_input: SDMXVectorInput) -> Dict[str, Any]:
        """
        Fetch time-series observations for a single StatCan vector via SDMX REST.

        Simpler alternative to get_sdmx_data when you already know the vectorId.
        Use get_series_info_from_cube_pid_coord or get_cube_metadata to find vectorIds.

        Time filtering:
          lastNObservations=5   → last 5 periods
          startPeriod="2020-01" → from Jan 2020 (monthly); "2020" for annual
          endPeriod="2023-12"   → up to Dec 2023

        Output rows contain: dimension values, "period", "value", SCALAR_FACTOR,
        UOM, VECTOR_ID, STATUS, and other SDMX attributes.

        IMPORTANT: Cite _sdmx_url and vectorId in your response.
        """
        vector_id = vector_input.vectorId
        url = f"{SDMX_BASE_URL}vector/v{vector_id}"

        params: Dict[str, Any] = {}
        if vector_input.lastNObservations is not None:
            params["lastNObservations"] = vector_input.lastNObservations
        if vector_input.startPeriod:
            params["startPeriod"] = vector_input.startPeriod
        if vector_input.endPeriod:
            params["endPeriod"] = vector_input.endPeriod

        async with httpx.AsyncClient(timeout=TIMEOUT_MEDIUM, verify=False) as client:
            response = await client.get(
                url, params=params, headers={"Accept": SDMX_JSON_ACCEPT}
            )
            response.raise_for_status()
            sdmx_url = str(response.url)
            rows = flatten_sdmx_json(response.json())

        result: Dict[str, Any] = {"_sdmx_url": sdmx_url, "row_count": len(rows)}
        if len(rows) > MAX_SDMX_ROWS:
            result["data"] = rows[:MAX_SDMX_ROWS]
            result["_truncated"] = True
            result["_message"] = (
                f"Response capped at {MAX_SDMX_ROWS} rows (total: {len(rows)}). "
                "Use lastNObservations or startPeriod/endPeriod to narrow the query."
            )
        else:
            result["data"] = rows
            result["_truncated"] = False

        return result

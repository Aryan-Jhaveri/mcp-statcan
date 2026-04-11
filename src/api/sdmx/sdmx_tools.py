"""SDMX REST API tools for Statistics Canada.

Provides server-side filtered data access via the SDMX REST API at:
  https://www150.statcan.gc.ca/t1/wds/sdmx/statcan/rest/

Four tools:
  get_sdmx_structure   — fetch Data Structure Definition (DSD) as JSON: dimensions + codelists
  get_sdmx_data        — fetch filtered observations by productId + key
  get_sdmx_vector_data — fetch observations for a single vectorId
  get_sdmx_rows        — fetch rows inline always (use when building artifacts/widgets)
"""

import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

import httpx

from ...config import (
    MAX_SDMX_ROWS,
    RENDER_BASE_URL,
    SDMX_BASE_URL,
    SDMX_JSON_ACCEPT,
    SDMX_XML_ACCEPT,
    TIMEOUT_MEDIUM,
)
from ...models.sdmx_models import (
    SDMXDataInput,
    SDMXKeyForDimensionInput,
    SDMXStructureInput,
    SDMXVectorInput,
)
from ...util.registry import ToolRegistry
from ...util.sdmx_json import flatten_sdmx_json
from ...util.truncation import DEFAULT_MEMBER_LIMIT

def _fix_or_series_keys(data: Dict[str, Any], key: str) -> None:
    """Fix StatCan's non-standard series key encoding for all queries.

    StatCan SDMX-JSON has two related bugs in series key encoding:

    Bug A — Solo/single-code queries (e.g. key "7.3.1.1.1.10.2"):
      StatCan uses the memberId as the series key index instead of the
      positional index (0) into the values array. Codes where memberId
      happens to equal 0 work correctly; all others produce an out-of-range
      index and lose their label (e.g. NOC=10 → series key index 10, but
      values has 1 entry at index 0).
      Fix: for any dim where the current index >= len(values), reset to 0.

    Bug B — OR queries (e.g. key "7.3.1.1.1.6+10+15.2"):
      For the OR dimension, code 1 uses positional index 0 (correct), but
      codes 2+ all use the same wrong index (the memberId of code 2), making
      them indistinguishable. Single-value dims after the OR dim use the
      global series index G instead of 0.
      Fix: derive G = min(obs_key) // n_period_vals for each series, then
      decompose G into per-dim positional indices (right-to-left for multiple
      OR dims).

    Operates in-place on the raw SDMX-JSON response dict.
    """
    key_parts = key.split(".")
    or_positions: Dict[int, List[str]] = {
        i: part.split("+")
        for i, part in enumerate(key_parts)
        if "+" in part
    }

    structure = data.get("structure", {})
    obs_dims = structure.get("dimensions", {}).get("observation", [])
    n_period_vals = len(obs_dims[0].get("values", [])) if obs_dims else 1
    if n_period_vals < 1:
        n_period_vals = 1

    series_dims: List[Dict] = structure.get("dimensions", {}).get("series", [])
    sorted_or_pos = sorted(or_positions.keys())

    dataset = (data.get("dataSets") or [{}])[0]
    raw_series: Dict[str, Any] = dataset.get("series", {})
    patched: Dict[str, Any] = {}

    for series_key_str, series_data in raw_series.items():
        parts = series_key_str.split(".")
        new_parts = list(parts)

        # Bug A fix: reset any out-of-range index on non-OR dims to 0.
        # Single-value dims should always use index 0; StatCan sometimes uses
        # memberId or global series index G instead.
        for dim_idx, dim in enumerate(series_dims):
            if dim_idx in or_positions or dim_idx >= len(new_parts):
                continue
            val_count = len(dim.get("values", []))
            if val_count > 0 and int(new_parts[dim_idx]) >= val_count:
                new_parts[dim_idx] = "0"

        # Bug B fix: for OR dims, replace index with G-derived positional index.
        if or_positions:
            obs_keys = [int(k) for k in series_data.get("observations", {}).keys()]
            if obs_keys:
                G = min(obs_keys) // n_period_vals
                remaining = G
                for pos in reversed(sorted_or_pos):
                    n = len(or_positions[pos])
                    new_parts[pos] = str(remaining % n)
                    remaining //= n

        patched[".".join(new_parts)] = series_data

    dataset["series"] = patched


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
    codelist_names: Dict[str, str] = {}  # cl_id → English name
    for cl in root.findall(".//str:Codelist", _NS):
        cl_id = cl.get("id", "")
        codelist_names[cl_id] = _get_english_name(cl)
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
                    "name": codelist_names.get(cl_id, "") if cl_id else "",
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

        IMPORTANT: In your final response to the user, you MUST cite the source of your data. 
        This means including the _sdmx_url.
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
          ".2.1"    = all geographies, Gender=2, Age=1  (wildcard — preferred for multi-geo)
          "1+2.2.1" = Geography 1 or 2, Gender=2, Age=1 (OR)

        IMPORTANT — key position codes:
          - Use member IDs from get_cube_metadata(), NOT SDMX codelist positions from
            get_sdmx_structure(). Member IDs and SDMX codelist codes are the same numbers.
          - Wildcard (omit a position) returns a SPARSE SAMPLE for large dimensions — do NOT
            use wildcard for dimensions with >30 codes (e.g. NOC occupations, CMA geographies).
            Use explicit member IDs joined with '+' instead.
          - To get all leaf IDs for a large dimension as a ready-to-use OR string, call
            get_sdmx_key_for_dimension(productId, dimension_position) first.

        Time filtering (use one or the other, not both):
          lastNObservations=12  → last 12 periods (e.g. 1 year of monthly data)
          startPeriod="2020"    → from 2020 onwards (annual); "2020-01" for monthly
          endPeriod="2023-12"   → up to Dec 2023

        LIMITATION: StatCan rejects combining lastNObservations with startPeriod/endPeriod (returns 406).
        NOTE: OR syntax (+) triggers a StatCan SDMX-JSON encoding bug (non-positional series keys).
          This is automatically corrected before rows are returned, so all OR-ed dimension labels
          should be present.

        Output rows contain: dimension values, "period", "value", SCALAR_FACTOR,
        UOM, VECTOR_ID, STATUS, and other SDMX attributes.

        Large responses: when row_count > 50 and RENDER_BASE_URL is configured, a download_csv
        URL is returned instead of inline data. Use it in a Python analysis tool:
          import pandas as pd; df = pd.read_csv(result["download_csv"])

        IMPORTANT: In your final response to the user, you MUST cite the source of your data.
        This means including the _sdmx_url, table information and productId/key in your response.
        """
        product_id = data_input.productId
        key = data_input.key

        if data_input.lastNObservations is not None and (data_input.startPeriod or data_input.endPeriod):
            raise ValueError(
                "StatCan SDMX does not support combining lastNObservations with startPeriod/endPeriod. "
                "Use lastNObservations=N for recent data, or startPeriod/endPeriod for a date range."
            )

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
            response_json = response.json()
            _fix_or_series_keys(response_json, key)
            rows = flatten_sdmx_json(response_json)

        result: Dict[str, Any] = {"_sdmx_url": sdmx_url, "row_count": len(rows)}

        # HTTP/Render mode: always return a CSV download URL — never inline data.
        # Data stays out of context; the caller fetches via script and writes to /tmp/.
        if RENDER_BASE_URL:
            import urllib.parse
            encoded_key = urllib.parse.quote(key, safe="")
            download_csv = f"{RENDER_BASE_URL}/files/sdmx/{product_id}/{encoded_key}"
            columns = list(rows[0].keys()) if rows else []
            result["columns"] = columns
            result["head"] = rows[:5]
            result["download_csv"] = download_csv
            result["_message"] = (
                f"{len(rows)} rows available. To get inline rows for analysis or artifact "
                f"embedding, call get_sdmx_rows with the same parameters: "
                f"productId={product_id}, key='{key}'"
                + (f", lastNObservations={data_input.lastNObservations}" if data_input.lastNObservations is not None else "")
                + (f", startPeriod='{data_input.startPeriod}'" if data_input.startPeriod else "")
                + (f", endPeriod='{data_input.endPeriod}'" if data_input.endPeriod else "")
                + ". It returns rows directly via the MCP connection — no external fetch required."
            )
            return result

        # stdio/local mode: inline data with truncation guard
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
    async def get_sdmx_rows(data_input: SDMXDataInput) -> Dict[str, Any]:
        """
        Fetch SDMX observations and always return rows inline — use this when you
        need to embed data in an artifact or widget.

        Unlike get_sdmx_data (which returns a download_csv URL in HTTP/Render mode),
        this tool always returns the full row list directly. Use it when:
          - Building a chart, table, or widget artifact that needs data embedded at
            construction time (browser-side fetch() from artifacts is blocked by CSP)
          - You need to sort/filter rows before embedding a small result set

        Same key syntax and time parameters as get_sdmx_data — see that tool's
        description for key construction rules and wildcard warnings.

        Rows are capped at MAX_SDMX_ROWS. For large dimensions use
        get_sdmx_key_for_dimension to build a precise OR key before calling this.

        IMPORTANT: In your final response to the user, cite the _sdmx_url, table
        productId, and key used.
        """
        product_id = data_input.productId
        key = data_input.key

        if data_input.lastNObservations is not None and (data_input.startPeriod or data_input.endPeriod):
            raise ValueError(
                "StatCan SDMX does not support combining lastNObservations with startPeriod/endPeriod. "
                "Use lastNObservations=N for recent data, or startPeriod/endPeriod for a date range."
            )

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
            response_json = response.json()
            _fix_or_series_keys(response_json, key)
            rows = flatten_sdmx_json(response_json)

        truncated = len(rows) > MAX_SDMX_ROWS
        return {
            "_sdmx_url": sdmx_url,
            "row_count": len(rows),
            "data": rows[:MAX_SDMX_ROWS],
            "_truncated": truncated,
            **({"_message": f"Capped at {MAX_SDMX_ROWS} rows (total: {len(rows)}). Narrow your key."} if truncated else {}),
        }

    @registry.tool()
    async def get_sdmx_vector_data(vector_input: SDMXVectorInput) -> Dict[str, Any]:
        """
        Fetch time-series observations for a single StatCan vector via SDMX REST.

        Simpler alternative to get_sdmx_data when you already know the vectorId.
        Use get_series_info_from_cube_pid_coord or get_cube_metadata to find vectorIds.

        Time filtering (use one or the other, not both):
          lastNObservations=5   → last 5 periods
          startPeriod="2020-01" → from Jan 2020 (monthly); "2020" for annual
          endPeriod="2023-12"   → up to Dec 2023

        LIMITATION: StatCan rejects combining lastNObservations with startPeriod/endPeriod (returns 406).

        Output rows contain: dimension values, "period", "value", SCALAR_FACTOR,
        UOM, VECTOR_ID, STATUS, and other SDMX attributes.

        IMPORTANT: In your final response to the user, you MUST cite the source of your data. 
        This means including the _sdmx_url,and vectorId in your response.
        """
        vector_id = vector_input.vectorId

        if vector_input.lastNObservations is not None and (vector_input.startPeriod or vector_input.endPeriod):
            raise ValueError(
                "StatCan SDMX does not support combining lastNObservations with startPeriod/endPeriod. "
                "Use lastNObservations=N for recent data, or startPeriod/endPeriod for a date range."
            )

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

    @registry.tool()
    async def get_sdmx_key_for_dimension(
        key_input: SDMXKeyForDimensionInput,
    ) -> Dict[str, Any]:
        """
        Return all leaf member IDs for a single dimension as a ready-to-use OR key string.

        Use this before get_sdmx_data when a dimension has many codes (e.g. 162 NOC minor
        groups, hundreds of CMA geographies). Avoids the need to call get_cube_metadata and
        manually parse a large JSON response.

        Leaf codes are codes with no children — the lowest-level members in a hierarchy.
        For flat (non-hierarchical) codelists every code is a leaf.

        Example:
          get_sdmx_key_for_dimension(productId=98100452, dimension_position=6)
          → {
              "dimension_id": "Occupation_...",
              "dimension_name": "Occupation - Minor group - NOC 2021",
              "position": 6,
              "leaf_count": 162,
              "total_count": 309,
              "or_key": "7+11+12+13+16+18+21+23+...",
              "note": "Paste or_key at position 6 in your get_sdmx_data key."
            }

        Then use the or_key directly:
          get_sdmx_data(productId=98100452, key="7.3.1.1.1.<or_key>.1", ...)
        """
        product_id = key_input.productId
        position = key_input.dimension_position

        # Fetch the DSD and extract the codelist for the requested dimension
        structure_url = f"{SDMX_BASE_URL}structure/Data_Structure_{product_id}"
        async with httpx.AsyncClient(timeout=TIMEOUT_MEDIUM, verify=False) as client:
            response = await client.get(
                structure_url, headers={"Accept": SDMX_XML_ACCEPT}
            )
            response.raise_for_status()

        parsed = _parse_structure_xml(response.text, product_id)
        dimensions: List[Dict[str, Any]] = parsed.get("dimensions", [])

        # Find the dimension at the requested 1-based position
        target_dim: Optional[Dict[str, Any]] = None
        for dim in dimensions:
            if dim.get("position") == position:
                target_dim = dim
                break

        if target_dim is None:
            available = sorted(d["position"] for d in dimensions)
            raise ValueError(
                f"No dimension at position {position} for productId {product_id}. "
                f"Available positions: {available}. Call get_sdmx_structure to see them."
            )

        # Re-parse the XML to get the FULL codelist (structure tool truncates at DEFAULT_MEMBER_LIMIT)
        root = ET.fromstring(response.text)
        cl_id = target_dim.get("codelist")
        all_codes: List[Dict[str, Any]] = []
        if cl_id:
            for cl in root.findall(".//str:Codelist", _NS):
                if cl.get("id") == cl_id:
                    for code in cl.findall("str:Code", _NS):
                        entry: Dict[str, Any] = {"id": code.get("id", "")}
                        parent_el = code.find("str:Parent", _NS)
                        if parent_el is not None:
                            pid = _find_ref_id(parent_el)
                            if pid:
                                entry["parent"] = pid
                        all_codes.append(entry)
                    break

        # Leaf codes = codes that are not referenced as a parent by any other code
        parent_ids = {c["parent"] for c in all_codes if "parent" in c}
        leaf_codes = [c for c in all_codes if c["id"] not in parent_ids]

        or_key = "+".join(c["id"] for c in leaf_codes)

        return {
            "dimension_id": target_dim.get("id"),
            "dimension_name": target_dim.get("name", ""),
            "position": position,
            "leaf_count": len(leaf_codes),
            "total_count": len(all_codes),
            "or_key": or_key,
            "note": (
                f"Paste or_key at position {position} in your get_sdmx_data key. "
                f"Leaf codes ({len(leaf_codes)}) are the lowest-level members — "
                f"parent nodes excluded."
            ),
        }

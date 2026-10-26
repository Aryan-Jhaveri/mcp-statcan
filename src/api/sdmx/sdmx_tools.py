"""SDMX REST API tools for Statistics Canada.

Provides server-side filtered data access via the SDMX REST API at:
  https://www150.statcan.gc.ca/t1/wds/sdmx/statcan/rest/

Tools:
  get_sdmx_structure   — fetch Data Structure Definition (DSD) as JSON: dimensions + codelists
  get_sdmx_data        — fetch filtered observations by productId + key
  get_sdmx_vector_data — fetch observations for a single vectorId
  query_sdmx           — fetch + run one SQL query server-side, return only the result
"""

import asyncio
import time
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Tuple

import httpx

from ...config import (
    MAX_CONCURRENT_EPHEMERAL_QUERIES,
    MAX_EPHEMERAL_ROWS,
    MAX_SDMX_ROWS,
    SDMX_BASE_URL,
    SDMX_DATA_XML_ACCEPT,
    SDMX_STRUCTURE_CACHE_TTL,
    SDMX_SUMMARY_MAX_SERIES,
    SDMX_SUMMARY_THRESHOLD,
    SDMX_STRUCTURE_TIMEOUT,
    SDMX_XML_ACCEPT,
)
from ..client import make_sdmx_get
from ...db.ephemeral import run_ephemeral_query

from ...models.sdmx_models import (
    SDMXDataInput,
    SDMXKeyForDimensionInput,
    SDMXKeyForDimensionOutput,
    SDMXQueryInput,
    SDMXQueryOutput,
    SDMXRowsOutput,
    SDMXStructureInput,
    SDMXStructureOutput,
    SDMXVectorInput,
)
from ...util.registry import READ_ONLY as _READ_ONLY, ToolRegistry
from ...util.sdmx_xml import check_sdmx_key, dataflow_id, flatten_sdmx_xml, group_rows_by_series, parse_dsd_labels, summarize_series
from ...util.sql_helpers import to_number
from ...util.truncation import DEFAULT_MEMBER_LIMIT

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


def _code_sort_key(code: Dict[str, Any]) -> Tuple[bool, int, str]:
    code_id = code["id"]
    return ("parent" in code, int(code_id) if code_id.isdigit() else 2**31, code_id)


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
        # Top-level codes (e.g. "Canada") first, then numeric order, so the truncated
        # preview shows the totals rather than whatever the DSD happens to list first
        codes.sort(key=_code_sort_key)
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


# productId → (fetched_at, structure XML text). Shared by data fetches (for labels)
# and the structure tools, so a typical structure → data workflow fetches the DSD once.
_structure_cache: Dict[int, Tuple[float, str]] = {}


async def fetch_structure_xml(product_id: int) -> str:
    """Fetch a table's Data Structure Definition (SDMX 2.1 XML), cached for an hour."""
    cached = _structure_cache.get(product_id)
    if cached and time.monotonic() - cached[0] < SDMX_STRUCTURE_CACHE_TTL:
        return cached[1]
    url = f"{SDMX_BASE_URL}structure/Data_Structure_{product_id}"
    response = await make_sdmx_get(url, headers={"Accept": SDMX_XML_ACCEPT}, timeout=SDMX_STRUCTURE_TIMEOUT)
    _structure_cache[product_id] = (time.monotonic(), response.text)
    return response.text


def _period_params(
    last_n: Optional[int], start_period: Optional[str], end_period: Optional[str]
) -> Dict[str, Any]:
    if last_n is not None and (start_period or end_period):
        raise ValueError(
            "StatCan SDMX does not support combining lastNObservations with startPeriod/endPeriod. "
            "Use lastNObservations=N for recent data, or startPeriod/endPeriod for a date range."
        )
    params: Dict[str, Any] = {}
    if last_n is not None:
        params["lastNObservations"] = last_n
    if start_period:
        params["startPeriod"] = start_period
    if end_period:
        params["endPeriod"] = end_period
    return params


async def fetch_sdmx_rows(
    product_id: int,
    key: str,
    last_n: Optional[int] = None,
    start_period: Optional[str] = None,
    end_period: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], str]:
    """Fetch SDMX data for productId + key and return (flattened rows, request URL).

    Shared by get_sdmx_data, get_sdmx_vector_data, query_sdmx, fetch_sdmx_to_database and
    the statcan CLI. Rows are not capped — callers decide whether to truncate or
    store them. Data and structure are fetched concurrently; see util/sdmx_xml.py
    for why data comes as XML rather than SDMX-JSON.
    """
    params = _period_params(last_n, start_period, end_period)
    url = f"{SDMX_BASE_URL}data/DF_{product_id}/{key}"
    data_task = asyncio.ensure_future(
        make_sdmx_get(url, params=params, headers={"Accept": SDMX_DATA_XML_ACCEPT})
    )
    try:
        dsd = parse_dsd_labels(await fetch_structure_xml(product_id))
        # A bad key can hang StatCan for over a minute, so stop the data request early
        problem = check_sdmx_key(key, dsd, product_id)
        if problem:
            raise ValueError(problem)
        try:
            response = await data_task
        except httpx.HTTPStatusError as exc:
            raise _explain_rejection(exc) from exc
    finally:
        if not data_task.done():
            data_task.cancel()
        elif not data_task.cancelled():
            data_task.exception()  # mark retrieved, so asyncio doesn't log it at GC
    rows = flatten_sdmx_xml(response.text, dsd)
    return rows, str(response.url)


def _explain_rejection(exc: httpx.HTTPStatusError) -> httpx.HTTPStatusError:
    """Re-word StatCan's 400/406 for a key that already matches the DSD. Keeps the
    exception type so callers (the CLI's exit codes) can still branch on status."""
    status = exc.response.status_code
    if status not in (400, 406):
        return exc
    return httpx.HTTPStatusError(
        f"StatCan rejected the query (HTTP {status}) for {exc.request.url}. The key matches "
        "the table's dimensions, so check the period format: '2024' (annual), "
        "'2024-01' (monthly), '2024-Q1' (quarterly).",
        request=exc.request,
        response=exc.response,
    )


async def fetch_sdmx_vector_rows(
    vector_id: int,
    last_n: Optional[int] = None,
    start_period: Optional[str] = None,
    end_period: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], str]:
    """Fetch observations for one vectorId and return (flattened rows, request URL).

    The table's productId (needed for labels) is read from the response header.
    """
    params = _period_params(last_n, start_period, end_period)
    url = f"{SDMX_BASE_URL}vector/v{vector_id}"
    response = await make_sdmx_get(url, params=params, headers={"Accept": SDMX_DATA_XML_ACCEPT})
    flow = dataflow_id(response.text)
    if flow is None:
        return [], str(response.url)
    structure_xml = await fetch_structure_xml(int(flow.removeprefix("DF_")))
    rows = flatten_sdmx_xml(response.text, parse_dsd_labels(structure_xml))
    return rows, str(response.url)


def _series_result(
    rows: List[Dict[str, Any]],
    sdmx_url: str,
    narrow_hint: str,
    full: bool = False,
    query_hint: str = "",
) -> Dict[str, Any]:
    """Tool output for get_sdmx_data / get_sdmx_vector_data.

    Above SDMX_SUMMARY_THRESHOLD observations (unless `full`), a summary of all rows:
    every later turn re-reads a tool result, so large row dumps slow the whole
    conversation (#139). Otherwise rows capped at MAX_SDMX_ROWS, grouped so each
    series' constant fields appear once.
    """
    if not full and len(rows) > SDMX_SUMMARY_THRESHOLD:
        all_series = group_rows_by_series(rows)
        summary = summarize_series(all_series, SDMX_SUMMARY_MAX_SERIES)
        shown = len(summary["series"])
        return {
            "_sdmx_url": sdmx_url,
            "row_count": len(rows),
            "series_count": len(all_series),
            "summary": True,
            **summary,
            "_truncated": False,
            "_message": (
                f"Summary of {len(rows)} observations in {len(all_series)} series"
                + (f" (first {shown} listed)" if shown < len(all_series) else "")
                + f". {query_hint}For every observation pass full=true (max {MAX_SDMX_ROWS}), "
                f"or narrow the request. {narrow_hint}"
            ),
        }

    truncated = len(rows) > MAX_SDMX_ROWS
    series = group_rows_by_series(rows[:MAX_SDMX_ROWS])
    result: Dict[str, Any] = {
        "_sdmx_url": sdmx_url,
        "row_count": len(rows),
        "series_count": len(series),
        "series": series,
        "_truncated": truncated,
    }
    if truncated:
        result["_message"] = (
            f"Response capped at {MAX_SDMX_ROWS} observations (total: {len(rows)}). {narrow_hint}"
        )
    return result


# Shared across requests: caps how many ephemeral queries run at once
_query_slots = asyncio.Semaphore(MAX_CONCURRENT_EPHEMERAL_QUERIES)


def register_sdmx_tools(registry: ToolRegistry) -> None:
    """Register all SDMX REST API tools with the MCP server."""

    @registry.tool(output_model=SDMXStructureOutput, annotations=_READ_ONLY)
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

        structure_xml = await fetch_structure_xml(product_id)
        result = _parse_structure_xml(structure_xml, product_id)
        result["_sdmx_url"] = url
        return result

    @registry.tool(output_model=SDMXRowsOutput, annotations=_READ_ONLY)
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
          - Wildcard (omit a position) returns EVERY member of that dimension, including
            totals and parent aggregates — on large dimensions (e.g. 309 NOC occupations) that
            can exceed the 500-row cap here; use query_sdmx or fetch_sdmx_to_database instead.
          - To sum or rank across a hierarchy without double-counting totals, use leaf codes:
            get_sdmx_key_for_dimension(productId, dimension_position) returns them as an OR key.

        Time filtering (use one or the other, not both):
          lastNObservations=12  → last 12 periods (e.g. 1 year of monthly data)
          startPeriod="2020"    → from 2020 onwards (annual); "2020-01" for monthly
          endPeriod="2023-12"   → up to Dec 2023

        LIMITATION: StatCan rejects combining lastNObservations with startPeriod/endPeriod (returns 406).

        Output is grouped by series: each entry in "series" holds the fields that are
        constant for that series once (dimension labels, _series_key, VECTOR_ID, UOM,
        SCALAR_FACTOR, ...) plus "observations" as [period, value] pairs with numeric
        values (null = suppressed). A third element {field: label} appears only on
        observations with their own attributes (e.g. a STATUS flag).

        Over 100 observations, the result is a summary instead (summary=true): fields
        shared by all series once in "common", varying dimensions in "varies", and per
        series count, period_range, latest, min and max. Pass full=true for every
        observation (capped at 500), or use query_sdmx to compute over all of them.

        Growth, percent change, averages, ranking or comparisons? Use query_sdmx instead
        of computing by hand from these values. Fetch each series and period range once:
        do not re-fetch periods you already have from get_sdmx_vector_data.

        IMPORTANT: In your final response to the user, you MUST cite the source of your data.
        This means including the _sdmx_url, table information and productId/key in your response.
        """
        rows, sdmx_url = await fetch_sdmx_rows(
            data_input.productId,
            data_input.key,
            data_input.lastNObservations,
            data_input.startPeriod,
            data_input.endPeriod,
        )
        return _series_result(
            rows,
            sdmx_url,
            "Narrow your query with a more specific key, or use "
            "lastNObservations / startPeriod / endPeriod.",
            full=data_input.full,
            query_hint=(
                "To compute over all of it (growth, ranking, averages), call query_sdmx with "
                "the same productId, key and period, plus sql over table 'data'. "
            ),
        )

    @registry.tool(output_model=SDMXQueryOutput, annotations=_READ_ONLY)
    async def query_sdmx(query_input: SDMXQueryInput) -> Dict[str, Any]:
        """
        Fetch SDMX observations and run ONE read-only SQL query over them server-side,
        returning only the query result. Nothing is stored — the data is loaded into a
        temporary in-memory table named `data` and discarded after the query.

        *** Use this for compute/compare/rank questions ("which province grew fastest",
        "average since 2020", "year-over-year change") instead of pulling raw rows with
        get_sdmx_data and doing arithmetic yourself. It is not limited to 500 rows. ***

        Same productId, key and time parameters as get_sdmx_data (see that tool for key
        syntax and wildcard rules). lastNObservations cannot be combined with
        startPeriod/endPeriod.

        Table `data` columns: one per dimension (names sanitized: spaces/punctuation → '_'),
        "period" (TEXT, e.g. "2024" or "2024-03"), "value" (REAL, NULL = suppressed),
        plus SDMX attributes like VECTOR_ID, UOM, SCALAR_FACTOR, STATUS.
        Quote mixed-case column names with double quotes.

        Example — CPI growth by province since Jan 2020:
          productId=18100004, key="2+3+5+6.2", startPeriod="2020-01",
          sql: SELECT "Geography",
                      MAX(CASE WHEN period = '2025-12' THEN value END) /
                      MAX(CASE WHEN period = '2020-01' THEN value END) - 1 AS growth
               FROM data GROUP BY 1 ORDER BY growth DESC

        If the SQL fails, the response includes `table_columns` — fix the query and retry.
        Limits: one statement, SELECT only, ~2s execution time, result capped at 500 rows.

        IMPORTANT: In your final response, cite the _sdmx_url, productId and key used.
        """
        rows, sdmx_url = await fetch_sdmx_rows(
            query_input.productId,
            query_input.key,
            query_input.lastNObservations,
            query_input.startPeriod,
            query_input.endPeriod,
        )

        if not rows:
            return {
                "error": "No observations returned for this query.",
                "_sdmx_url": sdmx_url,
                "hint": "Check the key against get_sdmx_structure and widen the period range.",
            }
        if len(rows) > MAX_EPHEMERAL_ROWS:
            return {
                "error": f"Query fetched {len(rows):,} rows, above the {MAX_EPHEMERAL_ROWS:,}-row limit.",
                "_sdmx_url": sdmx_url,
                "hint": "Narrow the key or the period range.",
            }

        for row in rows:
            row["value"] = to_number(row.get("value"))

        # Run off the event loop so a slow query can't stall other requests on the HTTP server
        async with _query_slots:
            result = await asyncio.to_thread(run_ephemeral_query, rows, query_input.sql)
        return {"_sdmx_url": sdmx_url, "fetched_row_count": len(rows), **result}

    @registry.tool(output_model=SDMXRowsOutput, annotations=_READ_ONLY)
    async def get_sdmx_vector_data(vector_input: SDMXVectorInput) -> Dict[str, Any]:
        """
        Fetch time-series observations for a single StatCan vector via SDMX REST.

        Simpler alternative to get_sdmx_data when you already know the vectorId.
        Use get_series_info (productId + coordinate) to find vectorIds.

        Time filtering (use one or the other, not both):
          lastNObservations=5   → last 5 periods
          startPeriod="2020-01" → from Jan 2020 (monthly); "2020" for annual
          endPeriod="2023-12"   → up to Dec 2023

        LIMITATION: StatCan rejects combining lastNObservations with startPeriod/endPeriod (returns 406).

        Output has the same shape as get_sdmx_data: one entry in "series" with its
        constant fields once, then "observations" as [period, value] pairs. Over 100
        observations it is a summary (latest, min, max) unless full=true.

        Growth, percent change or averages? Use query_sdmx instead of computing by hand.

        IMPORTANT: In your final response to the user, you MUST cite the source of your data.
        This means including the _sdmx_url and vectorId in your response.
        """
        rows, sdmx_url = await fetch_sdmx_vector_rows(
            vector_input.vectorId,
            vector_input.lastNObservations,
            vector_input.startPeriod,
            vector_input.endPeriod,
        )
        return _series_result(
            rows,
            sdmx_url,
            "Use lastNObservations or startPeriod/endPeriod to narrow the query.",
            full=vector_input.full,
        )

    @registry.tool(output_model=SDMXKeyForDimensionOutput, annotations=_READ_ONLY)
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
        structure_xml = await fetch_structure_xml(product_id)
        parsed = _parse_structure_xml(structure_xml, product_id)
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
        root = ET.fromstring(structure_xml)
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

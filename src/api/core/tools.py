"""Core tools: search, structure, data (+ sql), series info, changes.

Legacy → core:
  search_cubes_by_title                         → search_cubes_by_title
  get_sdmx_structure, get_sdmx_key_for_dimension → get_sdmx_structure (search, dimension)
  get_sdmx_data, get_sdmx_vector_data, query_sdmx → get_sdmx_data (vectorId, sql)
  get_series_info, get_series_info_from_vector, get_code_sets → get_series_info (codes decoded)
  get_changed_cube_list, get_changed_series_list,
  get_changed_series_data_from_vector / _cube_pid_coord → get_changes
"""

import asyncio
import datetime
from typing import Any, Dict, List, Optional

import httpx

from ...models.core_models import (
    CoreChangesInput,
    CoreDataInput,
    CoreDataOutput,
    CoreSearchInput,
    CoreSeriesInfoInput,
    CoreStructureInput,
    CoreStructureOutput,
)
from ...config import SDMX_BASE_URL, TIMEOUT_LARGE, TIMEOUT_MEDIUM
from ...util.coordinate import pad_coordinate
from ...util.registry import READ_ONLY, ToolRegistry
from ...util.truncation import DEFAULT_MEMBER_LIMIT
from ..client import make_get_request, make_post_request
from ..cube.discovery import search_catalogue, search_cubes
from ..metadata_tools import _fetch_code_sets
from ..sdmx.sdmx_tools import (
    _parse_structure_xml,
    _series_result,
    fetch_sdmx_rows,
    fetch_sdmx_vector_rows,
    fetch_structure_xml,
    query_rows,
)

# Codes listed for one dimension before asking for `search` instead
_MAX_DIMENSION_CODES = 200

_NO_CHANGE_TODAY = (
    "No change today for this series. This lists only today's changes (StatCan publishes "
    "at 08:30 ET). For past releases pass date; for the values, use get_sdmx_data."
)


def _statcan_today() -> str:
    """Today in Ottawa, where StatCan's release days are defined (the server may run in UTC)."""
    try:
        from zoneinfo import ZoneInfo
        tz: datetime.tzinfo = ZoneInfo("America/Toronto")
    except Exception:  # no tz database on this host
        tz = datetime.timezone(datetime.timedelta(hours=-5))
    return datetime.datetime.now(tz).date().isoformat()


def _leaf_key(codes: List[Dict[str, Any]]) -> str:
    """'+'-joined codes that are nobody's parent: summing them avoids double-counting totals."""
    parents = {c["parent"] for c in codes if "parent" in c}
    return "+".join(c["id"] for c in codes if c["id"] not in parents)


def _coordinate_to_key(coordinate: str) -> str:
    """WDS coordinate '14.2.0.0.0.0.0.0.0.0' → SDMX key '14.2' (0 = unused position)."""
    parts = coordinate.split(".")
    while parts and parts[-1] == "0":
        parts.pop()
    return ".".join(parts)


async def _decoders() -> Dict[str, Dict[int, str]]:
    """frequency / scalar / uom code → English label; empty if code sets are unavailable."""
    try:
        sets = await _fetch_code_sets()
    except (httpx.HTTPError, ValueError):
        return {}
    return {
        "frequency": {e["frequencyCode"]: e.get("frequencyDescEn") for e in sets.get("frequency", [])},
        "scalar": {e["scalarFactorCode"]: e.get("scalarFactorDescEn") for e in sets.get("scalar", [])},
        "uom": {e["memberUomCode"]: e.get("memberUomEn") for e in sets.get("uom", [])},
    }


def _slim_series(info: Dict[str, Any], dec: Dict[str, Dict[int, str]]) -> Dict[str, Any]:
    coordinate = info.get("coordinate", "")
    out: Dict[str, Any] = {
        "vectorId": info.get("vectorId"),
        "productId": info.get("productId"),
        "key": _coordinate_to_key(coordinate),
        "title": info.get("SeriesTitleEn"),
        "frequency": dec.get("frequency", {}).get(info.get("frequencyCode"), info.get("frequencyCode")),
        "uom": dec.get("uom", {}).get(info.get("memberUomCode"), info.get("memberUomCode")),
        "scalar": dec.get("scalar", {}).get(info.get("scalarFactorCode"), info.get("scalarFactorCode")),
        "decimals": info.get("decimals"),
    }
    if info.get("terminated"):
        out["terminated"] = True
    return out


def _split_wds(result_list: Any, inputs: List[Dict[str, Any]]):
    """WDS POST endpoints answer per item: split into (objects, failures)."""
    if not isinstance(result_list, list):
        raise ValueError(f"Unexpected WDS response: {str(result_list)[:200]}")
    ok, failed = [], []
    for given, item in zip(inputs, result_list):
        if isinstance(item, dict) and item.get("status") == "SUCCESS":
            ok.append(item.get("object", {}))
        else:
            failed.append({**given, "error": (item or {}).get("object") if isinstance(item, dict) else item})
    return ok, failed


async def _post_or_404(endpoint: str, payload: List[Dict[str, Any]]) -> Optional[Any]:
    """POST to WDS; None when it answers 404 (the getChangedSeriesData* 'no change today')."""
    try:
        return await make_post_request(endpoint, payload, timeout=TIMEOUT_MEDIUM)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            return None
        raise


def _page(items: List[Any], offset: int, limit: int, what: str) -> Dict[str, Any]:
    offset = max(offset, 0)
    page = items[offset:offset + limit]
    result: Dict[str, Any] = {what: page, "total": len(items)}
    if offset + len(page) < len(items):
        result["next_offset"] = offset + len(page)
    return result


def register_core_tools(registry: ToolRegistry) -> None:
    """Register the core toolset."""

    @registry.tool(annotations=READ_ONLY)
    async def search_cubes_by_title(search_input: CoreSearchInput) -> Dict[str, Any]:
        """Find StatCan tables by title keywords. Returns productId, title, dates and
        frequency; the top 3 include key_template, the dimension order of the SDMX key."""
        return await search_cubes(search_input.search_term, search_input.max_results, search_input.offset)

    @registry.tool(output_model=CoreStructureOutput, annotations=READ_ONLY)
    async def get_sdmx_structure(structure_input: CoreStructureInput) -> Dict[str, Any]:
        """A table's dimensions in key order with their codes (id, name, parent).
        Use search to find the codes for labels like 'Ontario' instead of guessing."""
        product_id = structure_input.productId
        position = structure_input.dimension
        terms = [t.strip().casefold() for t in (structure_input.search or "").split(";") if t.strip()]
        xml = await fetch_structure_xml(product_id)
        parsed = _parse_structure_xml(xml, product_id, member_limit=None if (terms or position) else DEFAULT_MEMBER_LIMIT)

        dims = parsed["dimensions"]
        result: Dict[str, Any] = {
            "name": parsed["name"],
            "productId": product_id,
            "key_template": ".".join(d["id"] for d in dims),
        }
        if position is not None:
            dims = [d for d in dims if d["position"] == position]
            if not dims:
                raise ValueError(
                    f"No dimension at position {position} in table {product_id}; "
                    f"it has {len(parsed['dimensions'])} (key_template {result['key_template']})."
                )
            result["leaf_key"] = _leaf_key(dims[0]["codes"])

        out_dims = []
        for d in dims:
            codes = d["codes"]
            entry = {"id": d["id"], "position": d["position"], "_code_count": d["_code_count"]}
            if terms:
                matched = [c for c in codes if any(t in c["name"].casefold() for t in terms)]
                if not matched:
                    # Show the usual preview (totals first) so the right label is visible
                    entry["_no_match"] = True
                    matched = codes[:DEFAULT_MEMBER_LIMIT]
                    entry["_truncated"] = len(codes) > DEFAULT_MEMBER_LIMIT
                codes = matched
            if len(codes) > _MAX_DIMENSION_CODES:
                entry["_truncated"] = True
                codes = codes[:_MAX_DIMENSION_CODES]
            elif d["_truncated"]:
                entry["_truncated"] = True
            if not entry.get("_truncated"):
                entry.pop("_truncated", None)
            entry["codes"] = codes
            out_dims.append(entry)
        result["dimensions"] = out_dims
        if any(d.get("_truncated") for d in out_dims):
            result["_message"] = (
                "Some code lists are cut short. Pass search='<label>' to find codes by name, or "
                "dimension=<position> for one full list. An empty key position means all codes."
            )
        if terms and all(d.get("_no_match") for d in out_dims):
            result["_message"] = f"No code names contain {structure_input.search!r}; try a shorter term."
        elif any(d.get("_no_match") for d in out_dims):
            result["_message"] = (
                "Dimensions marked _no_match had no code matching search; their first codes "
                "are shown instead (totals first)."
            )
        result["_sdmx_url"] = f"{SDMX_BASE_URL}structure/Data_Structure_{product_id}"
        return result

    @registry.tool(output_model=CoreDataOutput, annotations=READ_ONLY)
    async def get_sdmx_data(data_input: CoreDataInput) -> Dict[str, Any]:
        """Observations for productId + key, or one vectorId. Over 100 observations you get a
        per-series summary. Pass sql to compute over every row (growth, averages, ranking)
        server-side. Cite _sdmx_url."""
        d = data_input
        if d.vectorId is not None:
            if d.productId is not None or d.key is not None:
                raise ValueError("Pass either vectorId, or productId + key, not both.")
            rows, url = await fetch_sdmx_vector_rows(d.vectorId, d.lastNObservations, d.startPeriod, d.endPeriod)
            narrow = "Use lastNObservations or startPeriod/endPeriod to narrow it."
        elif d.productId is not None and d.key is not None:
            rows, url = await fetch_sdmx_rows(d.productId, d.key, d.lastNObservations, d.startPeriod, d.endPeriod)
            narrow = "Narrow the key, or use lastNObservations / startPeriod / endPeriod."
        elif d.productId is not None:
            raise ValueError(
                f"key is required with productId. get_sdmx_structure(productId={d.productId}) "
                "shows the dimension order and codes."
            )
        else:
            raise ValueError("Pass productId + key, or vectorId.")

        if d.sql:
            return await query_rows(rows, url, d.sql)
        return _series_result(
            rows, url, narrow, full=d.full,
            query_hint="To compute over all of it, call again with sql over table 'data'. ",
        )

    @registry.tool(annotations=READ_ONLY)
    async def get_series_info(info_input: CoreSeriesInfoInput) -> Dict[str, Any]:
        """Series metadata for productId + coordinates, or vectorIds: vectorId, key, title,
        frequency, unit of measure and scalar (decoded), decimals."""
        i = info_input
        if i.coordinates and i.productId is None:
            raise ValueError("coordinates need productId.")
        if not i.coordinates and not i.vectorIds:
            raise ValueError("Pass productId + coordinates, or vectorIds.")

        found: List[Dict[str, Any]] = []
        failures: List[Dict[str, Any]] = []
        decoders = asyncio.ensure_future(_decoders())  # cached for an hour; fetch alongside
        if i.coordinates:
            payload = [{"productId": i.productId, "coordinate": pad_coordinate(c)} for c in i.coordinates]
            given = [{"productId": i.productId, "coordinate": c} for c in i.coordinates]
            ok, bad = _split_wds(await make_post_request("/getSeriesInfoFromCubePidCoord", payload, timeout=TIMEOUT_MEDIUM), given)
            found += ok
            failures += bad
        if i.vectorIds:
            payload = [{"vectorId": v} for v in i.vectorIds]
            ok, bad = _split_wds(await make_post_request("/getSeriesInfoFromVector", payload, timeout=TIMEOUT_MEDIUM), payload)
            found += ok
            failures += bad

        dec = await decoders
        if not found:
            raise ValueError(f"No series found: {failures}")
        result: Dict[str, Any] = {"series": [_slim_series(s, dec) for s in found]}
        if failures:
            result["failures"] = failures
        return result

    @registry.tool(annotations=READ_ONLY)
    async def get_changes(changes_input: CoreChangesInput) -> Dict[str, Any]:
        """What StatCan released: tables updated on a date (default today), today's changed
        series in one table (productId), or today's new data points for one series
        (vectorId, or productId + coordinate)."""
        c = changes_input
        if c.vectorId is not None or c.coordinate is not None:
            if c.vectorId is not None:
                endpoint, payload = "/getChangedSeriesDataFromVector", [{"vectorId": c.vectorId}]
            elif c.productId is None:
                raise ValueError("coordinate needs productId.")
            else:
                endpoint = "/getChangedSeriesDataFromCubePidCoord"
                payload = [{"productId": c.productId, "coordinate": pad_coordinate(c.coordinate)}]
            result = await _post_or_404(endpoint, payload)
            if result is None:
                return {**payload[0], "changed": False, "message": _NO_CHANGE_TODAY}
            ok, bad = _split_wds(result, payload)
            if not ok:
                return {**payload[0], "changed": False, "message": _NO_CHANGE_TODAY, "wds": bad[0].get("error")}
            return {"changed": True, **ok[0]}

        if c.productId is not None:
            if c.date:
                raise ValueError("Per-table changes are only available for today; omit date.")
            try:
                result = await make_get_request("/getChangedSeriesList", timeout=TIMEOUT_LARGE)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 409:
                    raise ValueError("Today's changes are not released yet (StatCan publishes at 08:30 ET).")
                raise
            series = [s for s in result.get("object", []) if s.get("productId") == c.productId]
            out = _page(series, c.offset, c.limit, "series")
            out["productId"] = c.productId
            return out

        date = c.date or _statcan_today()
        try:
            datetime.date.fromisoformat(date)
        except ValueError:
            raise ValueError(f"date must be YYYY-MM-DD, got {date!r}.")
        result = await make_get_request(f"/getChangedCubeList/{date}", timeout=TIMEOUT_MEDIUM)
        if result.get("status") != "SUCCESS":
            raise ValueError(f"StatCan returned no change list for {date}: {result.get('object')}")
        titles = {t["productId"]: t.get("cubeTitleEn") for t in await search_catalogue()}
        tables = [
            {"productId": t["productId"], "title": titles.get(t["productId"]), "releaseTime": t.get("releaseTime")}
            for t in result.get("object", [])
        ]
        out = _page(tables, c.offset, c.limit, "tables")
        out["date"] = date
        return out

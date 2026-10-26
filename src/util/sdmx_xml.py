"""SDMX-ML (structure-specific XML) data parser for StatCan.

Why XML instead of SDMX-JSON: StatCan's SDMX-JSON encodes series keys and
attribute values as indices, and those indices are wrong in many responses
(issue #90). Series collide when decoded — which looks like wildcard queries
returning a "sparse sample" — and attributes such as VECTOR_ID, DGUID and UOM
land on the wrong rows. The structure-specific XML format puts dimension
codes and attribute values inline on each <Series>/<Obs>, so there is nothing
to mis-index:

  <Series Geography="2" Products_and_product_groups="2" VECTOR_ID="41690973" UOM="17">
    <Obs TIME_PERIOD="2026-08" OBS_VALUE="169.8"/>
  </Series>

Values are codes, so labels come from the table's Data Structure Definition
(codelists for dimensions and coded attributes). Output rows keep the same
shape the JSON flattener produced: one column per dimension (label), then
"_series_key", "period", "value", then attributes.
"""

import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

from .sql_helpers import to_number

_STR = "{http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure}"
_COM = "{http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common}"
_XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"
_OBS_RESERVED = ("TIME_PERIOD", "OBS_VALUE")
_MISSING = object()


def _norm(component_id: str) -> str:
    """Normalize a component id: the DSD keeps characters like '-' that StatCan's
    data XML replaces with '_' (e.g. 'Occupation_-_Minor_group' vs 'Occupation___Minor_group')."""
    return re.sub(r"[^0-9A-Za-z_]", "_", component_id)


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _english_name(el: ET.Element) -> Optional[str]:
    names = el.findall(f"{_COM}Name")
    for n in names:
        if n.get(_XML_LANG) == "en":
            return (n.text or "").strip()
    return (names[0].text or "").strip() if names else None


def _enumeration_ref(component: ET.Element) -> Optional[str]:
    enum = component.find(f".//{_STR}Enumeration")
    if enum is None:
        return None
    for child in enum:
        if _local(child.tag) == "Ref":
            return child.get("id")
    return None


def parse_dsd_labels(structure_xml: str) -> Dict[str, Any]:
    """Extract what's needed to label data rows from a StatCan DSD.

    Returns {"dimensions": [dimension ids in key-position order],
             "labels": {component_id: {code: English name}}} for every
    dimension and attribute that has a codelist. Ids are normalized with _norm
    so they match the attribute names used in data messages.
    """
    root = ET.fromstring(structure_xml)
    codelists: Dict[str, Dict[str, str]] = {}
    for cl in root.iter(f"{_STR}Codelist"):
        codelists[cl.get("id", "")] = {
            code.get("id", ""): (_english_name(code) or code.get("id", ""))
            for code in cl.findall(f"{_STR}Code")
        }

    dims = []
    labels: Dict[str, Dict[str, str]] = {}
    # Only DimensionList children: <str:Dimension> also appears elsewhere (e.g. constraints)
    for dim_list in root.iter(f"{_STR}DimensionList"):
        for dim in dim_list.findall(f"{_STR}Dimension"):
            dim_id = _norm(dim.get("id", ""))
            dims.append((int(dim.get("position", "0")), dim_id))
            cl_id = _enumeration_ref(dim)
            if cl_id in codelists:
                labels[dim_id] = codelists[cl_id]
    for attr_list in root.iter(f"{_STR}AttributeList"):
        for attr in attr_list.findall(f"{_STR}Attribute"):
            cl_id = _enumeration_ref(attr)
            if cl_id in codelists:
                labels[_norm(attr.get("id", ""))] = codelists[cl_id]

    return {"dimensions": [d for _, d in sorted(dims)], "labels": labels}


_KEY_CODE_SAMPLE = 5


def check_sdmx_key(key: str, dsd: Dict[str, Any], product_id: int) -> Optional[str]:
    """Return why `key` doesn't fit the table's DSD, or None if it does.

    StatCan's own errors don't say: too few positions is a 400 "Syntax error", too
    many a 406 "Wrong date format", an unknown code in the first position hangs the
    connection, and an unknown code elsewhere returns no rows.
    """
    dims = dsd["dimensions"]
    template = ".".join(dims)
    parts = key.split(".")
    if len(parts) != len(dims):
        return (
            f"Key '{key}' has {len(parts)} position(s); table {product_id} has {len(dims)}: "
            f"{template}. Use one position per dimension (empty = all members, "
            f"codes joined by '+' for OR), e.g. '{'.'.join(['1'] + [''] * (len(dims) - 1))}'."
        )
    for pos, (part, dim) in enumerate(zip(parts, dims), start=1):
        codes = dsd["labels"].get(dim)
        if not part or codes is None:
            continue
        unknown = [c for c in part.split("+") if c not in codes]
        if unknown:
            # Numeric order puts totals (Canada, All-items) first, unlike DSD order
            ordered = sorted(codes, key=lambda c: (not c.isdigit(), int(c) if c.isdigit() else 0, c))
            sample = ", ".join(f"{c} ({codes[c]})" for c in ordered[:_KEY_CODE_SAMPLE])
            return (
                f"Unknown code(s) {', '.join(repr(c) for c in unknown)} at position {pos} ({dim}) "
                f"of table {product_id}. {len(codes)} valid codes, e.g. {sample}. "
                "See get_sdmx_structure for the full list."
            )
    return None


def _parse_data(data_xml: str) -> ET.Element:
    """Parse a data message, tolerating StatCan's malformed empty result.

    When a query matches nothing, StatCan returns a stray closing tag with no
    opening one: '<message:DataSet ...></Series> </message:DataSet>'.
    """
    try:
        return ET.fromstring(data_xml)
    except ET.ParseError:
        if "<Series " not in data_xml and "</Series>" in data_xml:
            return ET.fromstring(data_xml.replace("</Series>", ""))
        raise


def dataflow_id(data_xml: str) -> Optional[str]:
    """The dataflow id (e.g. 'DF_18100004') from a data message header."""
    root = _parse_data(data_xml)
    for el in root.iter():
        if _local(el.tag) == "Ref" and el.get("id", "").startswith("DF_"):
            return el.get("id")
    return None


def flatten_sdmx_xml(data_xml: str, dsd: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Flatten a structure-specific SDMX-ML data message into tabular rows.

    dsd is the output of parse_dsd_labels for the same table.
    """
    root = _parse_data(data_xml)
    dim_ids: List[str] = dsd["dimensions"]
    labels: Dict[str, Dict[str, str]] = dsd["labels"]

    def label(component: str, code: str) -> str:
        return labels.get(component, {}).get(code, code)

    rows: List[Dict[str, Any]] = []
    for series in root.iter():
        if _local(series.tag) != "Series":
            continue
        s_attrs = {_norm(k): v for k, v in series.attrib.items()}
        base: Dict[str, Any] = {d: label(d, s_attrs[d]) for d in dim_ids if d in s_attrs}
        base["_series_key"] = ".".join(s_attrs.get(d, "") for d in dim_ids)
        series_attributes = {k: label(k, v) for k, v in s_attrs.items() if k not in dim_ids}

        for obs in series:
            if _local(obs.tag) != "Obs":
                continue
            o = obs.attrib
            value = o.get("OBS_VALUE")
            row = dict(base)
            row["period"] = o.get("TIME_PERIOD")
            row["value"] = None if value in (None, "", "NaN") else value
            row.update(series_attributes)
            row.update({_norm(k): label(_norm(k), v) for k, v in o.items() if k not in _OBS_RESERVED})
            rows.append(row)
    return rows


def group_rows_by_series(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Compact flat rows for tool output: fields that are constant within a series
    (dimensions, VECTOR_ID, UOM, ...) appear once per series, followed by
    "observations" as [period, value] pairs with numeric values. Fields that vary
    within a series (e.g. a STATUS on some observations) become a third element:
    [period, value, {field: label}].
    """
    by_key: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        by_key.setdefault(row.get("_series_key", ""), []).append(row)

    series_list: List[Dict[str, Any]] = []
    for series_rows in by_key.values():
        first = series_rows[0]
        constant = {
            k: v
            for k, v in first.items()
            if k not in ("period", "value") and all(r.get(k, _MISSING) == v for r in series_rows)
        }
        observations: List[List[Any]] = []
        for r in series_rows:
            obs: List[Any] = [r.get("period"), to_number(r.get("value"))]
            extra = {k: v for k, v in r.items() if k not in constant and k not in ("period", "value")}
            if extra:
                obs.append(extra)
            observations.append(obs)
        series_list.append({**constant, "observations": observations})
    return series_list



_SUMMARY_DROP = ("DGUID",)  # per-geography ids; long and rarely what the agent needs


def summarize_series(series_list: List[Dict[str, Any]], max_series: int, max_values: int = 10) -> Dict[str, Any]:
    """Summary of group_rows_by_series output, for results too large to return in full.

    Fields with the same value in every series go in "common" once; fields that vary
    are listed under "varies" with their distinct values. Each of the first
    `max_series` series keeps only its varying fields plus count, period range,
    latest, min and max as [period, value].
    """
    fields = [k for k in series_list[0] if k != "observations" and k not in _SUMMARY_DROP] if series_list else []
    common = {k: series_list[0][k] for k in fields if all(s.get(k, _MISSING) == series_list[0][k] for s in series_list)}
    varies: Dict[str, Dict[str, Any]] = {}
    for k in fields:
        if k in common or k in ("_series_key", "VECTOR_ID"):
            continue
        distinct = list(dict.fromkeys(s.get(k) for s in series_list))
        varies[k] = {"count": len(distinct), "values": distinct[:max_values]}

    periods = [o[0] for s in series_list for o in s["observations"]]
    summaries = []
    for s in series_list[:max_series]:
        obs = s["observations"]
        entry = {k: v for k, v in s.items() if k != "observations" and k not in common and k not in _SUMMARY_DROP}
        entry["count"] = len(obs)
        entry["period_range"] = [obs[0][0], obs[-1][0]]
        entry["latest"] = obs[-1][:2]
        numeric = [o for o in obs if isinstance(o[1], (int, float))]
        if numeric:
            entry["min"] = min(numeric, key=lambda o: o[1])[:2]
            entry["max"] = max(numeric, key=lambda o: o[1])[:2]
        summaries.append(entry)

    return {
        "period_range": [min(periods), max(periods)] if periods else [],
        "common": common,
        "varies": varies,
        "series": summaries,
    }

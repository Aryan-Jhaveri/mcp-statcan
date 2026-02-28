"""SDMX-JSON flattener: converts index-based compact encoding to tabular rows.

SDMX-JSON (application/vnd.sdmx.data+json;version=1.0.0-wd) uses positional
indices throughout to minimize payload size. Every dimension value, attribute value,
and observation period is stored as an integer index into a lookup table in
`data["structure"]`. This module dereferences all indices to produce readable rows.

Response structure overview:
  dataSets[0].series: dict mapping series key strings ("0.1.2") to series objects
    series key: dot-separated indices into structure.dimensions.series[n].values[idx]
    series.attributes: list of indices into structure.attributes.series[n].values[idx]
    series.observations: dict mapping obs key ("0") to obs value arrays
      obs key: index into structure.dimensions.observation[0].values[idx] (TIME_PERIOD)
      obs value: [dataValue, attr0_idx, attr1_idx, ...]
        obs value[0]: numeric or string data value (null = suppressed)
        obs value[1+]: indices into structure.attributes.observation[n].values[idx]
"""

from typing import Any, Dict, List, Optional


def _deref(lookup_list: List[Dict[str, Any]], idx: Optional[int]) -> Optional[str]:
    """Dereference an index into a SDMX values list. Returns 'name' if present, else 'id'."""
    if idx is None or not isinstance(idx, int):
        return None
    if idx < len(lookup_list):
        entry = lookup_list[idx]
        return entry.get("name") or entry.get("id")
    return None


def flatten_sdmx_json(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Flatten SDMX-JSON compact format into a list of tabular row dicts.

    Each output row contains:
    - One key per series dimension (e.g. "Geography", "Gender", "Age_group")
    - "period": the time period string (e.g. "2025" or "2023-01")
    - "value": the data value (numeric/string; None = suppressed)
    - One key per series attribute present in the response (e.g. "UOM", "DGUID")
    - One key per observation attribute present in the response
      (e.g. "SCALAR_FACTOR", "VECTOR_ID", "STATUS")

    Indices that are None or out-of-range are skipped silently.
    """
    structure = data.get("structure", {})
    dims = structure.get("dimensions", {})
    attrs = structure.get("attributes", {})

    series_dims: List[Dict] = dims.get("series", [])
    obs_dims: List[Dict] = dims.get("observation", [])
    series_attrs: List[Dict] = attrs.get("series", [])
    obs_attrs: List[Dict] = attrs.get("observation", [])

    rows: List[Dict[str, Any]] = []

    for dataset in data.get("dataSets", []):
        for series_key_str, series_data in dataset.get("series", {}).items():

            # --- Decode series dimensions ---
            series_indices = [int(i) for i in series_key_str.split(".")]
            dim_values: Dict[str, Any] = {}
            for pos, idx in enumerate(series_indices):
                if pos < len(series_dims):
                    dim = series_dims[pos]
                    val = _deref(dim.get("values", []), idx)
                    if val is not None:
                        dim_values[dim["id"]] = val

            # --- Decode series attributes ---
            series_attr_values: Dict[str, Any] = {}
            for pos, idx in enumerate(series_data.get("attributes", [])):
                if idx is not None and pos < len(series_attrs):
                    attr = series_attrs[pos]
                    val = _deref(attr.get("values", []), idx)
                    if val is not None:
                        series_attr_values[attr["id"]] = val

            # --- Decode observations ---
            for obs_key_str, obs_value in series_data.get("observations", {}).items():
                obs_idx = int(obs_key_str)
                row: Dict[str, Any] = dict(dim_values)

                # Time period — use "id" (the period string like "2025" or "2023-01")
                if obs_dims:
                    period_vals = obs_dims[0].get("values", [])
                    if obs_idx < len(period_vals):
                        row["period"] = period_vals[obs_idx].get("id") or period_vals[obs_idx].get("name")

                # Data value is the first element of the obs array
                row["value"] = obs_value[0] if obs_value else None

                # Decode observation attributes (obs_value[1], [2], ...)
                for pos, idx in enumerate(obs_value[1:] if obs_value else []):
                    if idx is not None and pos < len(obs_attrs):
                        attr = obs_attrs[pos]
                        val = _deref(attr.get("values", []), idx)
                        if val is not None:
                            row[attr["id"]] = val

                # Merge series attributes (obs-level takes priority on name clash)
                for k, v in series_attr_values.items():
                    if k not in row:
                        row[k] = v

                rows.append(row)

    return rows

"""Inputs and outputs for the core toolset (STATCAN_TOOLSET=core, src/api/core/).

Every model's JSON schema is published in tools/list on every turn, so schemas are
compacted: no "title" keys, and Optional[X] is published as X rather than
anyOf [X, null]. Pydantic still validates the full types.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _compact(node: Any) -> Any:
    if isinstance(node, dict):
        node = {k: _compact(v) for k, v in node.items() if k != "title"}
        any_of = node.get("anyOf")
        if isinstance(any_of, list):
            kept = [s for s in any_of if s != {"type": "null"}]
            if len(kept) == 1:
                node.pop("anyOf")
                node = {**kept[0], **node}
        if node.get("default", 0) is None:
            node.pop("default")
        return node
    if isinstance(node, list):
        return [_compact(v) for v in node]
    return node


class _CoreModel(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    @classmethod
    def model_json_schema(cls, *args, **kwargs) -> Dict[str, Any]:  # type: ignore[override]
        return _compact(super().model_json_schema(*args, **kwargs))


class _CoreInput(_CoreModel):
    model_config = ConfigDict(extra="forbid")


# ── Inputs ────────────────────────────────────────────────────────────────

class CoreSearchInput(_CoreInput):
    search_term: str = Field(..., description="Keywords, all must appear in the title (English or French).")
    max_results: int = 10
    offset: int = Field(0, description="next_offset from the previous page.")


class CoreStructureInput(_CoreInput):
    productId: int = Field(..., description="8-digit table id (table 18-10-0004-01 → 18100004).")
    search: Optional[str] = Field(
        None,
        description=(
            "Return only codes whose name contains this text (case-insensitive), across all "
            "dimensions, e.g. 'Ontario'. Separate several terms with ';'."
        ),
    )
    dimension: Optional[int] = Field(
        None,
        description=(
            "Key position: return every code of that dimension (default: first 10 per "
            "dimension), plus leaf_key, its lowest-level codes as a '+' OR."
        ),
    )


class CoreDataInput(_CoreInput):
    productId: Optional[int] = None
    key: Optional[str] = Field(
        None,
        description=(
            "With productId: one code per dimension in position order, joined by '.'; "
            "'+' for OR ('1+2.2'); empty for all members ('.2', includes totals)."
        ),
    )
    vectorId: Optional[int] = Field(None, description="Instead of productId + key: one series.")
    lastNObservations: Optional[int] = Field(None, description="Last N periods per series.")
    startPeriod: Optional[str] = Field(
        None, description="'2020', '2020-01' or '2020-Q1'. Not with lastNObservations."
    )
    endPeriod: Optional[str] = None
    sql: Optional[str] = Field(
        None,
        description=(
            "One SELECT over all fetched rows as table 'data', returning only its result. "
            "Use it for growth, averages, rankings. Columns: one per dimension (non-alphanumerics "
            "→ '_', double-quote them), period (TEXT), value (REAL), VECTOR_ID, UOM, STATUS."
        ),
    )
    full: bool = Field(
        False, description="Every observation (max 500) instead of a summary when over 100."
    )

    @field_validator("key", mode="before")
    @classmethod
    def _key_as_text(cls, v: Any) -> Any:
        if isinstance(v, bool) or isinstance(v, float):
            raise ValueError('key must be a string such as "2.2"; as a number it loses codes like "1.10"')
        return str(v) if isinstance(v, int) else v


class CoreSeriesInfoInput(_CoreInput):
    productId: Optional[int] = None
    coordinates: Optional[List[str]] = Field(
        None, description="With productId: dot-separated member ids, e.g. ['14.2']."
    )
    vectorIds: Optional[List[int]] = None


class CoreChangesInput(_CoreInput):
    date: Optional[str] = Field(
        None, description="YYYY-MM-DD: tables released that day (default today)."
    )
    productId: Optional[int] = Field(None, description="With coordinate: one series.")
    coordinate: Optional[str] = None
    vectorId: Optional[int] = Field(None, description="Today's changed data points for this series.")
    offset: int = 0
    limit: int = 50


# ── Outputs ───────────────────────────────────────────────────────────────
# Deliberately thin: outputSchema counts toward the tools/list budget, and the
# shape varies (rows / summary / sql result), so only what is always present.

class CoreDataOutput(_CoreModel):
    sdmx_url: str = Field(..., alias="_sdmx_url")


class CoreStructureOutput(_CoreModel):
    productId: int
    dimensions: List[Dict[str, Any]]
    sdmx_url: str = Field(..., alias="_sdmx_url")

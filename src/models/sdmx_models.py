from pydantic import BaseModel, ConfigDict, Field
from typing import Any, Dict, List, Optional


class SDMXStructureInput(BaseModel):
    productId: int


class SDMXDataInput(BaseModel):
    productId: int
    key: str = Field(
        ...,
        description=(
            "Dot-separated dimension codes in position order (e.g. '1.2.1'). "
            "Use '+' for OR ('1+2.2.1' = Geography 1 or 2). "
            "Omit a value for wildcard ('.2.1' = all geographies, Gender=2, Age=1). "
            "Code numbers match WDS memberIds — no translation needed. "
            "Call get_sdmx_structure first to see dimension positions and valid codes."
        ),
    )
    startPeriod: Optional[str] = Field(
        None, description="Start period in YYYY or YYYY-MM format."
    )
    endPeriod: Optional[str] = Field(
        None, description="End period in YYYY or YYYY-MM format."
    )
    lastNObservations: Optional[int] = Field(
        None,
        description="Return only the last N observations per series (e.g. 12 for one year of monthly data).",
    )


class SDMXQueryInput(SDMXDataInput):
    sql: str = Field(
        ...,
        description=(
            "One read-only SELECT (WITH/CTEs and window functions allowed) against table "
            "'data'. Columns: one per dimension (spaces/punctuation -> '_', e.g. "
            "\"Products_and_product_groups\"), period, value (REAL), VECTOR_ID, UOM, "
            "SCALAR_FACTOR, STATUS, etc. Quote mixed-case names: SELECT \"Geography\", ..."
        ),
    )


class SDMXVectorInput(BaseModel):
    vectorId: int
    startPeriod: Optional[str] = Field(
        None, description="Start period in YYYY or YYYY-MM format."
    )
    endPeriod: Optional[str] = Field(
        None, description="End period in YYYY or YYYY-MM format."
    )
    lastNObservations: Optional[int] = Field(
        None,
        description="Return only the last N observations (e.g. 5 for last 5 periods).",
    )


class SDMXKeyForDimensionInput(BaseModel):
    productId: int
    dimension_position: int = Field(
        ...,
        description=(
            "1-based position of the dimension in the SDMX key (use get_sdmx_structure "
            "to find positions). E.g. position=6 for the 6th dot-separated slot."
        ),
    )


# ── Output models ────────────────────────────────────────────────────────────
# Published as each tool's outputSchema (see ToolRegistry.tool(output_model=...)).
# They document the dicts the tools already return; extra="allow" keeps the
# schema open so adding a field never breaks clients validating structuredContent.
# Error results ({"error": ...}) are flagged isError and are not validated.

class _OpenModel(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)


class SDMXRowsOutput(_OpenModel):
    sdmx_url: str = Field(..., alias="_sdmx_url", description="SDMX request URL — cite as the data source.")
    row_count: int = Field(..., description="Total rows returned by StatCan (before truncation).")
    data: List[Dict[str, Any]] = Field(
        ..., description="Observation rows: dimension columns, period, value, and SDMX attributes."
    )
    truncated: bool = Field(..., alias="_truncated", description="True if data was capped at 500 rows.")
    message: Optional[str] = Field(None, alias="_message", description="Truncation guidance, when truncated.")


class SDMXQueryOutput(_OpenModel):
    sdmx_url: str = Field(..., alias="_sdmx_url", description="SDMX request URL — cite as the data source.")
    fetched_row_count: int = Field(..., description="Rows loaded into the temporary 'data' table.")
    columns: List[str] = Field(..., description="Columns of the SQL result.")
    rows: List[Dict[str, Any]] = Field(..., description="SQL result rows (max 500).")
    table_columns: List[str] = Field(..., description="Columns available in table 'data'.")
    message: Optional[str] = Field(None, description="Present when the result was truncated.")


class SDMXCode(_OpenModel):
    id: str
    name: str
    parent: Optional[str] = Field(None, description="Parent code id in the hierarchy, if any.")


class SDMXDimension(_OpenModel):
    id: str
    name: str
    position: int = Field(..., description="1-based slot in the dot-separated key.")
    codelist: Optional[str] = None
    codes: List[SDMXCode]
    code_count: int = Field(..., alias="_code_count")
    truncated: bool = Field(..., alias="_truncated")
    message: Optional[str] = Field(None, alias="_message")


class SDMXStructureOutput(_OpenModel):
    name: str
    productId: int
    dimensions: List[SDMXDimension]
    sdmx_url: str = Field(..., alias="_sdmx_url")


class SDMXKeyForDimensionOutput(_OpenModel):
    dimension_id: Optional[str] = None
    dimension_name: str
    position: int
    leaf_count: int
    total_count: int
    or_key: str = Field(..., description="'+'-joined leaf codes, ready to paste at `position` in the key.")
    note: str


class FetchSDMXToDatabaseOutput(_OpenModel):
    success: str
    sdmx_url: str = Field(..., alias="_sdmx_url")
    table: str
    columns: List[str]
    rows_inserted: int
    series_count: int
    period_range: Optional[List[str]] = Field(None, description="[first_period, last_period]")
    new: int = Field(..., description="Observations not previously stored.")
    revised: int = Field(..., description="Stored observations whose value changed.")
    unchanged: int = Field(..., description="Stored observations re-fetched with the same value.")
    sample: List[Dict[str, Any]]
    next_step: str

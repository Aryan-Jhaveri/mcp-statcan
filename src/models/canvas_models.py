from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ViewDataSource(BaseModel):
    """One named dataset bound into a view. The server fetches it; rows never pass through the model."""

    productId: Optional[int] = Field(None, description="StatCan table (with key). Same as get_sdmx_data.")
    key: Optional[str] = Field(
        None, description="SDMX key for productId, e.g. '1+2+5.2' (see get_sdmx_structure for positions)."
    )
    vectorId: Optional[int] = Field(None, description="A single series by vectorId, instead of productId + key.")
    startPeriod: Optional[str] = Field(None, description="YYYY or YYYY-MM.")
    endPeriod: Optional[str] = Field(None, description="YYYY or YYYY-MM.")
    lastNObservations: Optional[int] = Field(
        None, description="Last N per series. Cannot be combined with startPeriod/endPeriod."
    )
    sql: Optional[str] = Field(
        None,
        description=(
            "Optional read-only SELECT over the fetched rows (table `data`, same columns as query_sdmx). "
            "The query result becomes the dataset: aggregate, pivot or rank server-side before drawing."
        ),
    )
    rows: Optional[List[Dict[str, Any]]] = Field(
        None, description="Inline rows you already have (small, e.g. a computed summary). Max 2,000."
    )

    @model_validator(mode="after")
    def _one_source(self) -> "ViewDataSource":
        kinds = [self.productId is not None, self.vectorId is not None, self.rows is not None]
        if sum(kinds) != 1:
            raise ValueError("Each data source needs exactly one of: productId + key, vectorId, or rows.")
        if self.productId is not None and not self.key:
            raise ValueError("productId needs a key (use get_sdmx_structure to build one).")
        if self.rows is not None and self.sql:
            raise ValueError("sql runs over fetched StatCan rows; it can't be combined with inline rows.")
        return self


class RenderViewInput(BaseModel):
    title: str = Field(..., description="Short title shown above the view and in the browser tab.")
    html: Optional[str] = Field(
        None,
        description=(
            "Your view: any HTML body content with <style> and <script> (classic or type=module). "
            "Load libraries from cdn.jsdelivr.net, cdnjs.cloudflare.com, unpkg.com or esm.sh. "
            "Read data from statcan.data.<name> (see the tool description for the full statcan API)."
        ),
    )
    vega_lite: Optional[Dict[str, Any]] = Field(
        None,
        description=(
            "A Vega-Lite v6 spec, instead of html. Reference datasets by name: \"data\": {\"name\": \"cpi\"}. "
            "Use the `date` field with \"type\": \"temporal\" for time axes."
        ),
    )
    data: Dict[str, ViewDataSource] = Field(
        default_factory=dict,
        description="Named datasets, e.g. {\"cpi\": {\"productId\": 18100004, \"key\": \"2+5+6.2\", \"startPeriod\": \"2020-01\"}}.",
    )

    @model_validator(mode="after")
    def _one_body(self) -> "RenderViewInput":
        if (self.html is None) == (self.vega_lite is None):
            raise ValueError("Pass exactly one of html or vega_lite.")
        return self


class _OpenModel(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)


class ViewDataset(_OpenModel):
    columns: List[str]
    rows: List[Dict[str, Any]]
    row_count: int = Field(..., description="Rows before the per-dataset cap.")
    truncated: bool
    source_url: Optional[str] = Field(None, description="SDMX request URL, when fetched from StatCan.")


class RenderViewOutput(_OpenModel):
    view_id: str
    title: str
    url: Optional[str] = Field(None, description="Standalone page (hosted link or local file:// path).")
    html: Optional[str] = None
    vega_lite: Optional[Dict[str, Any]] = None
    datasets: Dict[str, ViewDataset]
    mcp_endpoint: Optional[str] = Field(None, description="Hosted MCP endpoint, for statcan.query in standalone pages.")

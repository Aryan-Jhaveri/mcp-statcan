import httpx
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from ..util.registry import ToolRegistry
from ..config import BASE_URL, TIMEOUT_LARGE, VERIFY_SSL
from ..util.logger import log_ssl_warning, log_data_validation_warning
from ..db.schema import create_table_from_data
from ..models.db_models import TableDataInput


class FetchVectorsInput(BaseModel):
    vectorIds: List[str] = Field(
        ...,
        description="List of StatCan vector IDs to fetch (e.g. ['111', '222', '333']). "
                    "Get these from get_cube_metadata → dimension members → vectorId field.",
    )
    table_name: str = Field(
        ...,
        description="Name of the SQLite table to create and populate. "
                    "Use snake_case, e.g. 'unemployment_by_province'.",
    )
    startRefPeriod: Optional[str] = Field(
        None,
        description="Start of the reference period to fetch, inclusive. Format: YYYY-MM-DD.",
    )
    endRefPeriod: Optional[str] = Field(
        None,
        description="End of the reference period to fetch, inclusive. Format: YYYY-MM-DD.",
    )


def register_composite_tools(registry: ToolRegistry):
    """Register high-level composite tools that orchestrate multiple API + DB steps."""

    @registry.tool()
    async def fetch_vectors_to_database(input_data: FetchVectorsInput) -> Dict[str, Any]:
        """
        PREFERRED tool for multi-series analysis. Fetches data for multiple StatCan
        vector IDs in a single API call and immediately stores the results in a SQLite
        table — no separate create/insert steps needed.

        *** USE THIS TOOL whenever you need data for multiple provinces, age groups,
        industries, or any other breakdown. It replaces the slow pattern of calling
        get_data_from_cube_pid_coord_and_latest_n_periods once per series. ***

        Typical workflow:
          1. search_cubes_by_title("unemployment rate") → find productId
          2. get_cube_metadata(productId=...) → find vectorIds for each series you want
          3. fetch_vectors_to_database(
               vectorIds=["v111","v222","v333"],
               table_name="unemployment_by_province",
               startRefPeriod="2023-01-01",
               endRefPeriod="2024-12-31"
             )  ← single call fetches + stores everything
          4. query_database("SELECT * FROM unemployment_by_province") → analyze

        Args:
            input_data.vectorIds: List of vector IDs to fetch (strings, e.g. ["111","222"]).
            input_data.table_name: SQLite table to create and populate.
            input_data.startRefPeriod: Optional start date (YYYY-MM-DD).
            input_data.endRefPeriod: Optional end date (YYYY-MM-DD).

        Returns:
            Dict with table name, columns, rows_inserted, and a 5-row sample so you
            can verify the data looks right before querying.

        IMPORTANT: In your final response cite the vectorIds and reference period used.
        """
        vector_ids = input_data.vectorIds
        table_name = input_data.table_name

        if not vector_ids:
            return {"error": "vectorIds list cannot be empty."}
        if not table_name.isidentifier():
            return {"error": f"Invalid table name: '{table_name}'. Use alphanumeric and underscores."}

        # Build query params
        params: Dict[str, Any] = {"vectorIds": ",".join(str(v) for v in vector_ids)}
        if input_data.startRefPeriod:
            params["startRefPeriod"] = input_data.startRefPeriod
        if input_data.endRefPeriod:
            params["endReferencePeriod"] = input_data.endRefPeriod

        # Fetch data from StatCan API
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT_LARGE, verify=VERIFY_SSL) as client:
            log_ssl_warning(f"SSL verification disabled for fetch_vectors_to_database.")
            try:
                response = await client.get("/getDataFromVectorByReferencePeriodRange", params=params)
                response.raise_for_status()
                result_list = response.json()
            except httpx.RequestError as exc:
                return {"error": f"Network error fetching vectors: {exc}"}
            except Exception as exc:
                return {"error": f"Unexpected error fetching vectors: {exc}"}

        # Process the response — flatten each vector's data points
        flat_rows: List[Dict[str, Any]] = []
        failures = []
        if not isinstance(result_list, list):
            return {"error": f"Unexpected API response format (not a list): {type(result_list)}"}

        for item in result_list:
            if not isinstance(item, dict):
                continue
            if item.get("status") == "SUCCESS":
                obj = item.get("object", {})
                vector_id = obj.get("vectorId")
                product_id = obj.get("productId")
                coordinate = obj.get("coordinate")
                data_points = obj.get("vectorDataPoint", [])
                if isinstance(data_points, list):
                    for point in data_points:
                        if isinstance(point, dict):
                            row = dict(point)
                            row["vectorId"] = vector_id
                            if product_id is not None:
                                row["productId"] = product_id
                            if coordinate is not None:
                                row["coordinate"] = coordinate
                            flat_rows.append(row)
            else:
                failures.append(item)
                log_data_validation_warning(f"Vector fetch partial failure: {item}")

        if not flat_rows:
            failure_detail = failures[:3] if failures else "No data returned."
            return {
                "error": "No data points retrieved from the API.",
                "failures": failure_detail,
                "hint": "Check that vectorIds are correct and the date range contains data.",
            }

        # Store in SQLite via create_table_from_data (creates + inserts in one shot)
        db_result = create_table_from_data(TableDataInput(table_name=table_name, data=flat_rows))

        if "error" in db_result:
            return {
                "error": f"Data fetched ({len(flat_rows)} rows) but failed to store: {db_result['error']}",
                "rows_fetched": len(flat_rows),
                "sample": flat_rows[:3],
            }

        # Return a summary with a small sample so the LLM can verify structure
        return {
            "success": db_result["success"],
            "table": table_name,
            "columns": db_result.get("columns", []),
            "rows_inserted": db_result.get("rows_inserted", len(flat_rows)),
            "partial_failures": len(failures),
            "sample": flat_rows[:5],
            "next_step": f"Use query_database to analyze: SELECT * FROM {table_name} LIMIT 10",
        }

import httpx
import sqlite3
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from ..util.registry import ToolRegistry
from ..config import BASE_URL, TIMEOUT_LARGE, TIMEOUT_MEDIUM, VERIFY_SSL
from ..util.logger import log_ssl_warning, log_data_validation_warning
from ..db.connection import get_db_connection
from ..db.store import create_series_view, upsert_sdmx_rows, upsert_wds_points
from mcp.types import ToolAnnotations

from ..models.sdmx_models import FetchSDMXToDatabaseOutput, SDMXDataInput
from .sdmx.sdmx_tools import fetch_sdmx_rows


class StoreCubeMetadataInput(BaseModel):
    productId: int = Field(..., description="The StatCan cube ProductId whose full metadata to fetch and store.")


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
    sample_size: Optional[int] = Field(
        5,
        description="Number of sample rows to include in the response preview. Default 5.",
    )


class FetchSDMXToDatabaseInput(SDMXDataInput):
    table_name: str = Field(
        ...,
        description="Name of the SQLite table to create and populate. "
                    "Use snake_case, e.g. 'cpi_by_province'. Overwrites an existing table.",
    )
    sample_size: Optional[int] = Field(
        5,
        description="Number of sample rows to include in the response preview. Default 5.",
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

        Storage: observations are upserted into the shared store (_statcan_series +
        _statcan_observations) and table_name becomes a VIEW with columns: dimension labels
        (when the series was also fetched via SDMX), series_key, period, ref_date, value,
        VECTOR_ID, UOM, SCALAR_FACTOR, STATUS, SYMBOL, release_time, product_id, fetched_at.
        The same series fetched via fetch_sdmx_to_database shares rows with this tool.

        Returns:
            Dict with view name, columns, rows_inserted, new/revised/unchanged counts, and a
            small sample so you can verify the data looks right before querying.

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

        if not isinstance(result_list, list):
            return {"error": f"Unexpected API response format (not a list): {type(result_list)}"}

        vectors: List[Dict[str, Any]] = []
        failures = []
        for item in result_list:
            if not isinstance(item, dict):
                continue
            if item.get("status") == "SUCCESS" and isinstance(item.get("object"), dict):
                vectors.append(item["object"])
            else:
                failures.append(item)
                log_data_validation_warning(f"Vector fetch partial failure: {item}")

        n_points = sum(len(v.get("vectorDataPoint") or []) for v in vectors)
        if not n_points:
            failure_detail = failures[:3] if failures else "No data returned."
            return {
                "error": "No data points retrieved from the API.",
                "failures": failure_detail,
                "hint": "Check that vectorIds are correct and the date range contains data.",
            }

        try:
            with get_db_connection() as conn:
                stored = upsert_wds_points(conn, vectors, source_url=str(response.url))
                columns = create_series_view(conn, table_name, stored["series_ids"], stored["date_range"])
                sample_size = input_data.sample_size or 5
                sample = [dict(r) for r in conn.execute(f'SELECT * FROM "{table_name}" LIMIT ?', (sample_size,))]
        except ValueError as exc:  # e.g. table_name is a canonical store table
            return {"error": str(exc)}
        except sqlite3.Error as exc:
            return {"error": f"Data fetched ({n_points} points) but failed to store: {exc}"}

        return {
            "success": f"Stored {n_points} observations for {len(stored['series_ids'])} series; "
                       f"'{table_name}' is a view over them.",
            "table": table_name,
            "columns": columns,
            "rows_inserted": n_points,
            "new": stored["inserted"],
            "revised": stored["revised"],
            "unchanged": stored["unchanged"],
            "partial_failures": len(failures),
            "sample": sample,
            "next_step": f"Use query_database to analyze: SELECT * FROM {table_name} LIMIT 10",
        }

    @registry.tool(
        output_model=FetchSDMXToDatabaseOutput,
        # Writes to the local DB and overwrites an existing table of the same name
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=True, openWorldHint=True),
    )
    async def fetch_sdmx_to_database(input_data: FetchSDMXToDatabaseInput) -> Dict[str, Any]:
        """
        PREFERRED tool for storing SDMX data. Fetches observations for a productId + key
        via SDMX and writes ALL rows straight into a SQLite table — the rows never pass
        through your context, and the MAX_SDMX_ROWS (500) cap does not apply.

        *** Use this instead of get_sdmx_data → create_table_from_data. Do NOT copy rows
        from get_sdmx_data into create_table_from_data — that sends every row through
        the context window twice. ***

        Same key syntax and time parameters as get_sdmx_data (see that tool for wildcard
        and OR-key rules). lastNObservations cannot be combined with startPeriod/endPeriod.

        Typical workflow:
          1. search_cubes_by_title("consumer price index") → productId
          2. get_sdmx_structure(productId=...) → dimension positions + codes
          3. fetch_sdmx_to_database(productId=18100004, key="2+3+4.2",
                                    startPeriod="2020-01", table_name="cpi_by_province")
          4. query_database("SELECT ... FROM cpi_by_province ...") → analyze

        Storage: observations are upserted into the shared store (_statcan_series +
        _statcan_observations, one row per series and period, with source and fetch time),
        and table_name becomes a VIEW over the series and periods this call fetched.
        Re-fetching updates values in place; new/revised/unchanged report what changed.
        For cross-table analysis, query the store directly, e.g.
          SELECT o.period, o.value FROM _statcan_observations o
          JOIN _statcan_series s USING (series_id) WHERE s.product_id = 18100004

        Returns a compact summary: view name, columns, rows_inserted, series_count,
        period range, new/revised/unchanged counts, a small sample, and the _sdmx_url.

        IMPORTANT: In your final response, cite the _sdmx_url, productId and key used.
        """
        table_name = input_data.table_name
        if not table_name.isidentifier():
            return {"error": f"Invalid table name: '{table_name}'. Use alphanumeric and underscores."}

        rows, sdmx_url = await fetch_sdmx_rows(
            input_data.productId,
            input_data.key,
            input_data.lastNObservations,
            input_data.startPeriod,
            input_data.endPeriod,
        )

        if not rows:
            return {
                "error": "No observations returned for this query.",
                "_sdmx_url": sdmx_url,
                "hint": "Check the key against get_sdmx_structure and widen the period range.",
            }

        try:
            with get_db_connection() as conn:
                stored = upsert_sdmx_rows(conn, input_data.productId, rows, sdmx_url)
                columns = create_series_view(conn, table_name, stored["series_ids"], stored["date_range"])
                sample_size = input_data.sample_size or 5
                sample = [dict(r) for r in conn.execute(f'SELECT * FROM "{table_name}" LIMIT ?', (sample_size,))]
        except ValueError as exc:  # e.g. table_name is a canonical store table
            return {"error": str(exc), "_sdmx_url": sdmx_url}
        except sqlite3.Error as exc:
            return {"error": f"Data fetched ({len(rows)} rows) but failed to store: {exc}", "_sdmx_url": sdmx_url}

        periods = [r["period"] for r in rows if r.get("period") is not None]
        return {
            "success": f"Stored {len(rows)} observations for {len(stored['series_ids'])} series; "
                       f"'{table_name}' is a view over them.",
            "_sdmx_url": sdmx_url,
            "table": table_name,
            "columns": columns,
            "rows_inserted": len(rows),
            "series_count": len(stored["series_ids"]),
            "period_range": [min(periods), max(periods)] if periods else None,
            "new": stored["inserted"],
            "revised": stored["revised"],
            "unchanged": stored["unchanged"],
            "sample": sample,
            "next_step": f"Use query_database to analyze: SELECT * FROM {table_name} LIMIT 10",
        }


    @registry.tool()
    async def store_cube_metadata(input_data: StoreCubeMetadataInput) -> Dict[str, Any]:
        """
        Fetches FULL metadata for a cube and stores it into two normalized SQLite
        tables (_statcan_dimensions, _statcan_members) without returning the full
        data to the context window.

        Use this when you need to browse all dimension members or look up vectorIds.
        The summary returned by get_cube_metadata only shows 5 members per dimension —
        call this tool first, then use SQL to drill into specific dimensions.

        Typical workflow:
          1. store_cube_metadata(productId=1234567)
             → stores all members + vectorIds, returns compact summary
          2. query_database("SELECT * FROM _statcan_dimensions WHERE pid = 1234567")
             → see all dimension names and member counts
          3. query_database("SELECT member_name_en, vector_id FROM _statcan_members
                             WHERE pid = 1234567 AND dim_index = 2")
             → browse all members for a specific dimension
          4. fetch_vectors_to_database(vectorIds=[...], ...) → fetch the data

        Tables are shared across multiple pids — calling this for a new pid adds
        rows without affecting data for other pids already stored.

        Returns a compact summary: dimension names + member counts + example SQL.

        IMPORTANT: Cite the productId and cubeTitleEn in your final response.
        """
        pid = input_data.productId

        async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT_MEDIUM, verify=VERIFY_SSL) as client:
            log_ssl_warning(f"SSL verification disabled for store_cube_metadata pid={pid}.")
            try:
                response = await client.post("/getCubeMetadata", json=[{"productId": pid}])
                response.raise_for_status()
                result_list = response.json()
            except httpx.RequestError as exc:
                return {"error": f"Network error fetching cube metadata: {exc}"}

        if not (isinstance(result_list, list) and result_list and result_list[0].get("status") == "SUCCESS"):
            msg = result_list[0].get("object") if result_list else "Unknown error"
            return {"error": f"API did not return SUCCESS for productId {pid}: {msg}"}

        metadata = result_list[0]["object"]
        dimensions = metadata.get("dimension", [])

        dim_rows = [
            {
                "pid": pid,
                "dim_index": i,
                "dim_name_en": dim.get("dimensionNameEn"),
                "dim_name_fr": dim.get("dimensionNameFr"),
                "member_count": len(dim.get("member", [])),
            }
            for i, dim in enumerate(dimensions)
        ]

        member_rows = [
            {
                "pid": pid,
                "dim_index": i,
                "member_id": member.get("memberId"),
                "member_name_en": member.get("memberNameEn"),
                "member_name_fr": member.get("memberNameFr"),
                "vector_id": str(member["vectorId"]) if member.get("vectorId") is not None else None,
                "classification_code": member.get("classificationCode"),
            }
            for i, dim in enumerate(dimensions)
            for member in dim.get("member", [])
        ]

        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS "_statcan_dimensions" (
                        pid INTEGER,
                        dim_index INTEGER,
                        dim_name_en TEXT,
                        dim_name_fr TEXT,
                        member_count INTEGER
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS "_statcan_members" (
                        pid INTEGER,
                        dim_index INTEGER,
                        member_id INTEGER,
                        member_name_en TEXT,
                        member_name_fr TEXT,
                        vector_id TEXT,
                        classification_code TEXT
                    )
                """)
                cursor.execute('DELETE FROM "_statcan_dimensions" WHERE pid = ?', (pid,))
                cursor.execute('DELETE FROM "_statcan_members" WHERE pid = ?', (pid,))
                cursor.executemany(
                    'INSERT INTO "_statcan_dimensions" VALUES (?,?,?,?,?)',
                    [(r["pid"], r["dim_index"], r["dim_name_en"], r["dim_name_fr"], r["member_count"]) for r in dim_rows],
                )
                cursor.executemany(
                    'INSERT INTO "_statcan_members" VALUES (?,?,?,?,?,?,?)',
                    [(r["pid"], r["dim_index"], r["member_id"], r["member_name_en"], r["member_name_fr"], r["vector_id"], r["classification_code"]) for r in member_rows],
                )
                conn.commit()
        except sqlite3.Error as exc:
            return {"error": f"SQLite error storing cube metadata: {exc}"}

        return {
            "success": f"Stored metadata for productId {pid}.",
            "pid": pid,
            "cube_title_en": metadata.get("cubeTitleEn"),
            "dimensions": [
                {"dim_index": r["dim_index"], "dim_name_en": r["dim_name_en"], "member_count": r["member_count"]}
                for r in dim_rows
            ],
            "total_members_stored": len(member_rows),
            "next_steps": [
                f"SELECT * FROM _statcan_dimensions WHERE pid = {pid}",
                f"SELECT member_name_en, vector_id FROM _statcan_members WHERE pid = {pid} AND dim_index = 0",
            ],
        }

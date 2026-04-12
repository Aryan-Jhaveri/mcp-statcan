from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    GetPromptResult,
    ImageContent,
    EmbeddedResource,
    Prompt,
    PromptArgument,
    PromptMessage,
    TextContent,
    Tool,
)
import argparse
import asyncio
import contextlib
import os
import re
import sys

# Use relative imports within the src package
from . import config
from .api.cube import register_cube_tools
from .api.vector import register_vector_tools
from .api.metadata_tools import register_metadata_tools
from .api.composite_tools import register_composite_tools
from .api.sdmx import register_sdmx_tools
from .db.queries import register_db_tools
from .util.logger import log_server_debug
from .util.registry import registry


def create_server(http_mode: bool = False):
    """Create and configure the MCP server with all tools registered.

    Args:
        http_mode: If True, skip DB and composite tools (stateless HTTP proxy).
    """
    log_server_debug("Inside create_server function.")

    # Initialize standard MCP Server
    server = Server("StatCanAPI_Server")
    log_server_debug("MCP Server instance created.")

    # Register all tools by module to the global registry
    try:
        log_server_debug("Registering metadata tools...")
        register_metadata_tools(registry)
        log_server_debug("Registering cube tools...")
        register_cube_tools(registry)
        log_server_debug("Registering vector tools...")
        register_vector_tools(registry)

        if not http_mode:
            log_server_debug("Registering composite tools...")
            register_composite_tools(registry)

        log_server_debug("Registering SDMX tools...")
        register_sdmx_tools(registry)

        if not http_mode:
            log_server_debug("Registering db tools...")
            register_db_tools(registry)

        log_server_debug("Tool registration complete.")

    except Exception as e:
        log_server_debug(f"ERROR during tool registration: {e}")
        raise

    # Register handlers with the server instance
    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return registry.get_tools()

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent | ImageContent | EmbeddedResource]:
        try:
            result = await registry.call_tool(name, arguments)

            # Format result to MCP Content list
            if isinstance(result, list) or isinstance(result, dict):
                import json
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
            elif result is None:
                return [TextContent(type="text", text="Tool executed successfully with no output.")]
            else:
                return [TextContent(type="text", text=str(result))]

        except Exception as e:
            log_server_debug(f"Error calling tool {name}: {e}")
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    # ── MCP Prompts ────────────────────────────────────────────────────────
    from .prompts import _PROMPTS, get_prompt_text

    @server.list_prompts()
    async def list_prompts() -> list[Prompt]:
        return list(_PROMPTS.values())

    @server.get_prompt()
    async def get_prompt(name: str, arguments: dict | None = None) -> GetPromptResult:
        if name not in _PROMPTS:
            raise ValueError(f"Unknown prompt: {name}")

        args = arguments or {}
        text = get_prompt_text(name, args)

        return GetPromptResult(
            description=_PROMPTS[name].description,
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(type="text", text=text),
                )
            ],
        )

        elif name == "sdmx-key-builder":
            text = (
                "SDMX key construction guide for get_sdmx_data and statcan download --key:\n"
                "\n"
                "KEY FORMAT: dot-separated codes, one per dimension position (left to right).\n"
                '  "1.2.1"     = position-1 code 1, position-2 code 2, position-3 code 1\n'
                '  "1+2.2.1"   = position-1 code 1 OR 2, position-2 code 2, position-3 code 1\n'
                '  ".2.1"      = wildcard position-1 (all values), position-2 code 2, position-3 code 1\n'
                "\n"
                "WHICH CODES TO USE:\n"
                "  - Use member IDs from get_cube_metadata() or SDMX codelist code IDs\n"
                "  - WDS memberIds == SDMX codelist codes — same numbers, no translation needed\n"
                "  - Do NOT use the positional index of a code within get_sdmx_structure() output\n"
                "\n"
                "WILDCARD WARNING:\n"
                "  Wildcard (.) on a large dimension (>30 codes) returns only a sparse, unpredictable sample.\n"
                "  For NOC (309 codes), wildcard returned 31 rows; the correct full fetch needs 162 IDs.\n"
                "  Use get_sdmx_key_for_dimension(productId, dimension_position) to get the full OR key.\n"
                "\n"
                "OR KEY USAGE:\n"
                '  or_key from get_sdmx_key_for_dimension = "7+11+12+13+..." → paste at the right position:\n'
                '  key = f"7.3.1.1.1.{or_key}.1"\n'
                "\n"
                "TIME PARAMETERS (use only one, not both):\n"
                "  lastNObservations=N  → last N periods per series\n"
                '  startPeriod="YYYY"   → from year (or "YYYY-MM" for monthly)\n'
                '  endPeriod="YYYY-MM"  → up to this period\n'
                "  Combining lastNObservations + startPeriod/endPeriod → 406 error from StatCan.\n"
                "\n"
                "CLI USAGE (statcan download --key):\n"
                '  statcan download <product-id> --key "1.2.1+2.1" --last 12 --output ./data.csv\n'
                "  statcan download <product-id> --last 5 --dry-run   # preview SDMX URL before fetching\n"
                "\n"
                "INLINE ROWS VIA MCP TOOL (Claude.ai — use this instead of curl):\n"
                "  get_sdmx_rows(productId=<product-id>, key=\"<key>\", lastNObservations=12)\n"
                "  get_sdmx_rows(productId=<product-id>, key=\"<key>\", startPeriod=\"2020\", endPeriod=\"2024\")\n"
                "  → Returns rows directly — no external URL fetch needed.\n"
                "  → Rows are capped at 500. result[\"data\"] is the list of dicts.\n"
                "\n"
                "CLI (curl / statcan CLI):\n"
                f"  {render_base}/files/sdmx/<product-id>/<key>?lastNObservations=12\n"
                f"  statcan download <product-id> --key \"<key>\" --last 12 --output ./data.csv"
            )

        elif name == "statcan-download":
            pid = args.get("product_id", "<product-id>")
            last_n = args.get("last_n", "12")
            _safe_pid = re.sub(r"[^a-zA-Z0-9\-]", "_", str(pid))
            out = args.get("output_path", f"./statcan_{_safe_pid}.csv")
            text = (
                f"Download Statistics Canada table {pid}\n"
                "\n"
                "━━━ Claude Code (bash sandbox) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "\n"
                "# 1. Download data\n"
                f"statcan download {pid} --last {last_n} --output {out}\n"
                "\n"
                "# 2. Inspect column layout (note column numbers for filtering)\n"
                f"head -2 {out}\n"
                "\n"
                "# 3. Row count\n"
                f"awk 'NR>1' {out} | wc -l\n"
                "\n"
                "# 4. Unique values in first dimension (e.g. Geography)\n"
                f"awk -F',' 'NR>1 {{print $1}}' {out} | sort -u\n"
                "\n"
                "# 5. Unique values in second dimension (e.g. Sex, Industry)\n"
                f"awk -F',' 'NR>1 {{print $2}}' {out} | sort -u\n"
                "\n"
                "# 6. Filter to one dimension value\n"
                f"awk -F',' 'NR>1 && $1==\"Canada\"' {out}\n"
                "\n"
                "# 7. Top 10 by value (replace N with value column number from step 2)\n"
                f"awk -F',' 'NR>1' {out} | sort -t',' -rn -k N | head -10\n"
                "\n"
                "# 8. Time series for one geography (replace col numbers from step 2)\n"
                f"awk -F',' 'NR>1 && $1==\"Canada\" {{print $period_col, $value_col}}' {out} | sort -k1\n"
                "\n"
                "# 9. Latest period per vector (dedup by VECTOR_ID column)\n"
                f"sort -t',' -k period_col,period_col -r {out} | awk -F',' '!seen[$vector_col]++'\n"
                "\n"
                "# 10. Count non-empty values (exclude suppressed observations)\n"
                f"awk -F',' 'NR>1 && $value_col!=\"\"' {out} | wc -l\n"
                "\n"
                "Replace period_col, value_col, vector_col with actual column numbers from step 2.\n"
                "\n"
                "━━━ Claude.ai web (Python script) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "\n"
                "Step 1 — Get the table structure to build a key:\n"
                f"  get_sdmx_structure(productId={pid})\n"
                "  → For large dimensions (>30 codes):\n"
                f"  get_sdmx_key_for_dimension(productId={pid}, dimension_position=N)\n"
                "\n"
                "Step 2 — Fetch rows inline via MCP tool:\n"
                f"  get_sdmx_rows(productId={pid}, key=\"<key>\", lastNObservations={last_n})\n"
                "  → Returns rows directly in the tool response — no external fetch needed.\n"
                "  → Rows are capped at 500. result[\"data\"] is the list of dicts.\n"
                "\n"
                "Step 3 — Analyze the returned rows:\n"
                "  rows = result[\"data\"]\n"
                "  cols = list(rows[0].keys()) if rows else []\n"
                "  print(\"Rows:\", len(rows), \"Cols:\", cols)\n"
                "  top10 = sorted(rows, key=lambda r: float(r.get(\"value\",\"0\") or 0), reverse=True)[:10]\n"
                "  for r in top10: print(r.get(\"period\"), r.get(\"value\"))"
            )

        elif name == "statcan-vector-pipeline":
            vids = args.get("vector_ids", "<v41690973 v41690974>")
            out = args.get("output_path", "./statcan_vectors.csv")
            text = (
                f"Multi-series vector pipeline: {vids}\n"
                "\n"
                "# 1. Download vectors\n"
                f"statcan vector {vids} --last 12 --output {out}\n"
                "\n"
                "# 2. Inspect column layout (VECTOR_ID and period columns are key)\n"
                f"head -2 {out}\n"
                "\n"
                "# 3. Unique vector IDs in the result\n"
                f"awk -F',' 'NR>1 {{print $vector_col}}' {out} | sort -u\n"
                "\n"
                "# 4. Row count per vector\n"
                f"awk -F',' 'NR>1 {{print $vector_col}}' {out} | sort | uniq -c | sort -rn\n"
                "\n"
                "# 5. Time series for each vector (period + value)\n"
                f"awk -F',' 'NR>1 {{print $vector_col, $period_col, $value_col}}' {out} | sort -k1,1 -k2,2\n"
                "\n"
                "# 6. Latest observation per vector\n"
                f"sort -t',' -k period_col,period_col -r {out} | awk -F',' '!seen[$vector_col]++'\n"
                "\n"
                "# 7. Cross-series at a specific period (replace YYYY with target year)\n"
                f"awk -F',' 'NR>1 && $period_col==\"YYYY\"' {out}\n"
                "\n"
                "# 8. Period-over-period change per vector\n"
                f"awk -F',' 'NR>1 {{print $vector_col, $period_col, $value_col}}' {out} \\\n"
                "    | sort -k1,1 -k2,2 \\\n"
                "    | awk '{if (prev_vec==$1) print $1, $2, $3-prev_val; prev_vec=$1; prev_val=$3}'\n"
                "\n"
                "Replace vector_col, period_col, value_col with actual column numbers from step 2."
            )

        else:  # statcan-explore
            pid = args.get("product_id", "<product-id>")
            _safe_pid = re.sub(r"[^a-zA-Z0-9\-]", "_", str(pid))
            sample_out = f"./explore_{_safe_pid}.csv"
            text = (
                f"Explore Statistics Canada table {pid} before full download\n"
                "\n"
                "━━━ Claude Code (bash sandbox) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "\n"
                "# 1. Check table structure (dimensions, member counts)\n"
                f"statcan metadata {pid}\n"
                "\n"
                "# 2. Sample 3 most recent periods to see column layout\n"
                f"statcan download {pid} --last 3 --output {sample_out}\n"
                f"head -2 {sample_out}             # column names and positions\n"
                f"awk 'NR>1' {sample_out} | wc -l  # rows in 3-period sample\n"
                "\n"
                "# 3. Unique values in each dimension (adapt column numbers from step 2)\n"
                f"awk -F',' 'NR>1 {{print $1}}' {sample_out} | sort -u   # dim 1 (e.g. Geography)\n"
                f"awk -F',' 'NR>1 {{print $2}}' {sample_out} | sort -u   # dim 2 (e.g. Sex)\n"
                f"awk -F',' 'NR>1 {{print $3}}' {sample_out} | sort -u   # dim 3 (e.g. Industry)\n"
                "\n"
                "# 4. Estimate full dataset size\n"
                "#    rows_per_3_periods = result from step 2\n"
                "#    series_count = rows_per_3_periods / 3\n"
                "#    full_rows(last N) = series_count × N\n"
                "#    Use --key to narrow the query if size would be too large.\n"
                "\n"
                "# 5. Preview SDMX URL without downloading\n"
                f"statcan download {pid} --last 5 --dry-run\n"
                "\n"
                "# 6. Download with a focused key after exploring\n"
                f"statcan download {pid} --key \"1.1.1\" --last 24 --output ./data_{_safe_pid}.csv\n"
                "\n"
                "━━━ Claude.ai web (Python script) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "\n"
                "Step 1 — Check structure without fetching data (MCP tool):\n"
                f"  get_sdmx_structure(productId={pid})\n"
                "  → Count dimensions and codes. Note large dims (>30 codes).\n"
                "  → For large dims, call get_sdmx_key_for_dimension to get a narrow key first.\n"
                "\n"
                "Step 2 — Sample 3 periods to see column layout (MCP tool):\n"
                f"  get_sdmx_rows(productId={pid}, key=\"<narrow-key>\", lastNObservations=3)\n"
                "  → key from Step 1 — avoid wildcards on large dims.\n"
                "  → Returns rows in result[\"data\"].\n"
                "  rows = result[\"data\"]\n"
                "  cols = list(rows[0].keys()) if rows else []\n"
                "  print(\"Columns:\", cols)\n"
                "  print(\"Sample rows (3 periods):\", len(rows))\n"
                "  print(\"Estimated series:\", len(rows) // 3)\n"
                "  print(\"Projected rows for 12 periods: ~\", (len(rows) // 3) * 12)\n"
                "\n"
                "Step 3 — Estimate size and decide.\n"
                "  If projected rows are too large, narrow the key further.\n"
                "  Then call get_sdmx_rows with lastNObservations=12 for the full fetch."
            )

        return GetPromptResult(
            description=_PROMPTS[name].description,
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(type="text", text=text),
                )
            ],
        )

    log_server_debug("Returning server instance from create_server.")
    return server


async def _run_stdio():
    log_server_debug("Starting StatCan MCP Server on stdio...")
    server = create_server(http_mode=False)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


def _run_http(host: str, port: int):
    """Start the Streamable HTTP server (stateless, no DB tools)."""
    try:
        import uvicorn
        from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
        from starlette.applications import Starlette
        from starlette.middleware.cors import CORSMiddleware
        from starlette.requests import Request
        from starlette.responses import JSONResponse, Response
        from starlette.routing import Mount, Route
    except ImportError as e:
        print(f"HTTP transport requires uvicorn and starlette: {e}", file=sys.stderr)
        sys.exit(1)

    from .landing import landing_page

    log_server_debug(f"Starting StatCan MCP Server on HTTP {host}:{port}...")
    server = create_server(http_mode=True)

    session_manager = StreamableHTTPSessionManager(
        app=server,
        event_store=None,   # no resumability needed for stateless proxy
        json_response=False,  # SSE streaming (recommended)
        stateless=True,       # fresh context per request, horizontally scalable
    )

    async def handle_mcp(scope, receive, send):
        await session_manager.handle_request(scope, receive, send)

    async def health(request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok"})

    async def sdmx_csv(request: Request) -> Response:
        """Stateless SDMX → CSV proxy. Fetches StatCan SDMX, returns flattened CSV."""
        import csv
        import io
        import urllib.parse

        import httpx as _httpx

        from . import config as _cfg
        from .util.sdmx_json import flatten_sdmx_json as _flatten
        from .api.sdmx.sdmx_tools import _fix_or_series_keys

        product_id = request.path_params["product_id"]
        key = urllib.parse.unquote(request.path_params["key"])
        url = f"{_cfg.SDMX_BASE_URL}data/DF_{product_id}/{key}"

        params = {k: v for k, v in request.query_params.items()}
        try:
            async with _httpx.AsyncClient(timeout=_cfg.TIMEOUT_MEDIUM, verify=False) as client:
                resp = await client.get(
                    url, params=params,
                    headers={"Accept": _cfg.SDMX_JSON_ACCEPT},
                )
                resp.raise_for_status()
                data = resp.json()
                _fix_or_series_keys(data, key)
                rows = _flatten(data)
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=502)

        if not rows:
            return Response(content="", media_type="text/csv")

        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
        return Response(
            content=buf.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="sdmx_{product_id}.csv"'},
        )

    @contextlib.asynccontextmanager
    async def lifespan(app):
        async with session_manager.run():
            yield

    app = Starlette(
        routes=[
            Route("/", landing_page),
            Route("/health", health),
            Route("/files/sdmx/{product_id}/{key:path}", sdmx_csv),
            Mount("/mcp", app=handle_mcp),
        ],
        lifespan=lifespan,
    )
    app = CORSMiddleware(
        app,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["*"],
        expose_headers=["Mcp-Session-Id"],
    )

    uvicorn.run(app, host=host, port=port)


def main():
    """Sync entry point for the console script."""
    parser = argparse.ArgumentParser(description="Statistics Canada MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default=config.TRANSPORT,
        help="Transport mode: 'stdio' (default, local) or 'http' (remote, stateless)",
    )
    parser.add_argument(
        "--host",
        default=config.HOST,
        help="Host to bind in HTTP mode (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=config.PORT,
        help="Port to bind in HTTP mode (default: 8000)",
    )
    parser.add_argument(
        "--db-path",
        help="Path to the SQLite database file (default: ~/.statcan-mcp/statcan_data.db)",
    )
    args = parser.parse_args()

    # Override DB_FILE if --db-path was provided
    if args.db_path:
        db_path = os.path.expanduser(args.db_path)
        config.DB_FILE = db_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)

    if args.transport == "http":
        _run_http(args.host, args.port)
    else:
        try:
            asyncio.run(_run_stdio())
        except Exception as e:
            log_server_debug(f"UNEXPECTED ERROR in main block: {e}")
            import traceback
            traceback.print_exc(file=sys.stderr)


if __name__ == "__main__":
    main()

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    GetPromptResult,
    ImageContent,
    EmbeddedResource,
    Prompt,
    PromptMessage,
    TextContent,
    Tool,
)
import argparse
import asyncio
import contextlib
import os
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
    _PROMPTS = {
        "statcan-data-lookup": Prompt(
            name="statcan-data-lookup",
            description=(
                "Step-by-step guide for finding and fetching Statistics Canada data. "
                "Covers table discovery, SDMX structure, key construction, and data fetch."
            ),
        ),
        "sdmx-key-builder": Prompt(
            name="sdmx-key-builder",
            description=(
                "Guide for building a precise SDMX key for get_sdmx_data. "
                "Explains wildcard vs explicit member IDs, OR syntax, and dimension positions."
            ),
        ),
    }

    @server.list_prompts()
    async def list_prompts() -> list[Prompt]:
        return list(_PROMPTS.values())

    @server.get_prompt()
    async def get_prompt(name: str, arguments: dict | None = None) -> GetPromptResult:
        if name == "statcan-data-lookup":
            return GetPromptResult(
                description=_PROMPTS[name].description,
                messages=[
                    PromptMessage(
                        role="user",
                        content=TextContent(
                            type="text",
                            text="""Statistics Canada data lookup workflow:

Step 1 — Find the table:
  search_cubes_by_title(keywords=["labour", "force"]) → pick productId

Step 2 — Understand the dimensions:
  get_sdmx_structure(productId=...) → see dimension positions + sample codes
  Note: codes are truncated to 10 per dimension; use get_sdmx_key_for_dimension for full lists.

Step 3 — For dimensions with >30 codes (e.g. NOC occupations, CMA geographies):
  get_sdmx_key_for_dimension(productId=..., dimension_position=N)
  → returns or_key (all leaf codes joined with +) ready to paste into the key

Step 4 — Fetch the data:
  get_sdmx_data(productId=..., key="1.3.1.<or_key>.1", lastNObservations=5)

WARNING: Wildcard (omitting a dimension position) returns a SPARSE SAMPLE for large
dimensions — do NOT use wildcard for dimensions with more than ~30 codes.
Always use explicit member IDs or get_sdmx_key_for_dimension for reliable results.

IMPORTANT: Always cite the _sdmx_url, productId, and table title in your final answer.""",
                        ),
                    )
                ],
            )
        if name == "sdmx-key-builder":
            return GetPromptResult(
                description=_PROMPTS[name].description,
                messages=[
                    PromptMessage(
                        role="user",
                        content=TextContent(
                            type="text",
                            text="""SDMX key construction guide for get_sdmx_data:

KEY FORMAT: dot-separated codes, one per dimension position (left to right).
  "1.2.1"     = position-1 code 1, position-2 code 2, position-3 code 1
  "1+2.2.1"   = position-1 code 1 OR 2, position-2 code 2, position-3 code 1
  ".2.1"      = wildcard position-1 (all values), position-2 code 2, position-3 code 1

WHICH CODES TO USE:
  - Use member IDs from get_cube_metadata() or SDMX codelist code IDs
  - WDS memberIds == SDMX codelist codes — same numbers, no translation needed
  - Do NOT use the positional index of a code within get_sdmx_structure() output

WILDCARD WARNING:
  Wildcard (.) on a large dimension (>30 codes) returns only a sparse, unpredictable sample.
  For NOC (309 codes), wildcard returned 31 rows; the correct full fetch needs 162 IDs.
  Use get_sdmx_key_for_dimension(productId, dimension_position) to get the full OR key.

OR KEY USAGE:
  or_key from get_sdmx_key_for_dimension = "7+11+12+13+..." → paste at the right position:
  key = f"7.3.1.1.1.{or_key}.1"

TIME PARAMETERS (use only one, not both):
  lastNObservations=N  → last N periods per series
  startPeriod="YYYY"   → from year (or "YYYY-MM" for monthly)
  endPeriod="YYYY-MM"  → up to this period
  Combining lastNObservations + startPeriod/endPeriod → 406 error from StatCan.""",
                        ),
                    )
                ],
            )
        raise ValueError(f"Unknown prompt: {name}")

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

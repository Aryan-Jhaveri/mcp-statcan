from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
import argparse
import asyncio
import contextlib
import os
import sys

# Use relative imports within the src package
from . import config
from .api.cube_tools import register_cube_tools
from .api.vector_tools import register_vector_tools
from .api.metadata_tools import register_metadata_tools
from .api.composite_tools import register_composite_tools
from .api.sdmx_tools import register_sdmx_tools
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
        from starlette.responses import JSONResponse
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

    @contextlib.asynccontextmanager
    async def lifespan(app):
        async with session_manager.run():
            yield

    app = Starlette(
        routes=[
            Route("/health", health),
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

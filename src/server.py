from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolResult,
    EmbeddedResource,
    GetPromptResult,
    Icon,
    ImageContent,
    ListPromptsResult,
    ListToolsResult,
    Prompt,
    PromptArgument,
    PromptMessage,
    TextContent,
    Tool,
)
import argparse
import asyncio
import contextlib
import logging
import os
import re
import sys

_access_logger = logging.getLogger("statcan.access")


# StatCan flag icon advertised in serverInfo.icons on every initialize response.
# In mcp SDK v1.x this required a private-API monkey-patch on ServerSession
# (no public API for icons). Since mcp v2.x, `Server(icons=...)` and
# `Tool/Prompt(icons=...)` accept Icon objects directly, so the patch is gone.
_SERVER_ICONS = [
    Icon(
        src="https://raw.githubusercontent.com/Aryan-Jhaveri/mcp-statcan/main/assets/Flag.jpg",
        mime_type="image/jpeg",
        sizes=["206x109"],
    )
]

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

    from .prompts import _PROMPTS, get_prompt_text

    # ── v2 handler callables (ctx, params) → Result models ────────────────
    async def _on_list_tools(ctx, params) -> ListToolsResult:
        return ListToolsResult(tools=registry.get_tools())

    async def _on_call_tool(ctx, params) -> CallToolResult:
        name = params.name
        arguments = params.arguments or {}
        _access_logger.info("tool_call tool=%s", name)
        try:
            result = await registry.call_tool(name, arguments)

            # Format result to MCP Content list
            if isinstance(result, (list, dict)):
                import json
                content = [TextContent(type="text", text=json.dumps(result, indent=2))]
            elif result is None:
                content = [TextContent(type="text", text="Tool executed successfully with no output.")]
            else:
                content = [TextContent(type="text", text=str(result))]

            return CallToolResult(content=content)

        except Exception as e:
            log_server_debug(f"Error calling tool {name}: {e}")
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error: {str(e)}")],
                is_error=True,
            )

    async def _on_list_prompts(ctx, params) -> ListPromptsResult:
        return ListPromptsResult(prompts=list(_PROMPTS.values()))

    async def _on_get_prompt(ctx, params) -> GetPromptResult:
        name = params.name
        arguments = params.arguments
        if name not in _PROMPTS:
            raise ValueError(f"Unknown prompt: {name}")

        args = dict(arguments) if arguments else {}
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

    from importlib.metadata import PackageNotFoundError, version as _pkg_version
    try:
        _server_version = _pkg_version("statcan-mcp-server")
    except PackageNotFoundError:
        _server_version = "0.0.0"

    # Native icons support (mcp v2.x) — no more ServerSession patching.
    server = Server(
        "StatCanAPI_Server",
        version=_server_version,
        icons=_SERVER_ICONS,
        on_list_tools=_on_list_tools,
        on_call_tool=_on_call_tool,
        on_list_prompts=_on_list_prompts,
        on_get_prompt=_on_get_prompt,
    )
    log_server_debug("MCP Server instance created.")

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
        from mcp.server.auth.routes import create_auth_routes
        from mcp.server.auth.settings import ClientRegistrationOptions, RevocationOptions
        from pydantic import AnyHttpUrl
        from starlette.applications import Starlette
        from starlette.middleware.cors import CORSMiddleware
        from starlette.requests import Request
        from starlette.responses import JSONResponse, Response
        from starlette.routing import Mount, Route
    except ImportError as e:
        print(f"HTTP transport requires uvicorn and starlette: {e}", file=sys.stderr)
        sys.exit(1)

    from .landing import landing_page
    from .auth import PublicOAuthProvider

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

    async def well_known_mcp(request: Request) -> JSONResponse:
        from importlib.metadata import version as _pkg_version
        base = os.environ.get("RENDER_BASE_URL", "").rstrip("/")
        return JSONResponse({
            "name": "Statistics Canada MCP Server",
            "description": "Canadian statistical data via WDS and SDMX APIs — no API key required",
            "version": _pkg_version("statcan-mcp-server"),
            "endpointUrl": f"{base}/mcp/" if base else "/mcp/",
            "authentication": {"type": "none"},
            "repository": "https://github.com/Aryan-Jhaveri/mcp-statcan",
            "license": "MIT",
        })

    async def robots_txt(request: Request) -> Response:
        return Response(
            content=(
                "User-agent: *\n"
                "Disallow: /mcp/\n"
                "Allow: /\n"
                "Allow: /health\n"
                "Allow: /.well-known/\n"
                "Crawl-delay: 10\n"
            ),
            media_type="text/plain",
        )

    @contextlib.asynccontextmanager
    async def lifespan(app):
        async with session_manager.run():
            yield

    # OAuth 2.1 / PKCE — required for Claude.ai web connector tool routing.
    # PublicOAuthProvider auto-approves all clients; no user login is shown.
    # The MCP endpoint itself remains open (no token enforcement) so existing
    # programmatic and Claude Desktop access is unaffected.
    base_url = os.environ.get("RENDER_BASE_URL", f"http://localhost:{port}").rstrip("/")
    oauth_provider = PublicOAuthProvider()
    oauth_routes = create_auth_routes(
        provider=oauth_provider,
        issuer_url=AnyHttpUrl(base_url),
        service_documentation_url=AnyHttpUrl("https://github.com/Aryan-Jhaveri/mcp-statcan"),
        client_registration_options=ClientRegistrationOptions(enabled=True),
        revocation_options=RevocationOptions(enabled=True),
    )

    # Starlette's Mount("/mcp", ...) issues a 307 redirect when the path is
    # exactly "/mcp" (no trailing slash). Many MCP clients don't follow POST
    # redirects, so they silently fail. This middleware rewrites /mcp → /mcp/
    # before routing, eliminating the redirect entirely.
    class _NormalizeMcpPath:
        __slots__ = ("_app",)

        def __init__(self, app):
            self._app = app

        async def __call__(self, scope, receive, send):
            if scope.get("type") == "http" and scope.get("path") == "/mcp":
                scope = {**scope, "path": "/mcp/", "raw_path": b"/mcp/"}
            await self._app(scope, receive, send)

    starlette_app = Starlette(
        routes=[
            Route("/", landing_page),
            Route("/health", health),
            Route("/robots.txt", robots_txt),
            Route("/.well-known/mcp.json", well_known_mcp),
            Mount("/mcp", app=handle_mcp),
            *oauth_routes,
        ],
        lifespan=lifespan,
    )
    app = _NormalizeMcpPath(
        CORSMiddleware(
            starlette_app,
            allow_origins=["*"],
            allow_methods=["GET", "POST", "DELETE"],
            allow_headers=["*"],
            expose_headers=["Mcp-Session-Id"],
        )
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

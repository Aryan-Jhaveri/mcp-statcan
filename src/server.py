from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
import asyncio
import os
import sys

# Use relative imports within the src package
from .config import DB_FILE
from .api.cube_tools import register_cube_tools
from .api.vector_tools import register_vector_tools
from .api.metadata_tools import register_metadata_tools
from .db.queries import register_db_tools
from .util.logger import log_server_debug 
from .util.registry import registry

def create_server():
    """Create and configure the MCP server with all tools registered."""
    log_server_debug("Inside create_server function.")
    
    # Initialize standard MCP Server
    server = Server("StatCanAPI_DB_Server")
    log_server_debug("MCP Server instance created.")

    # Register all tools by module to the global registry
    try:
        log_server_debug("Registering metadata tools...")
        register_metadata_tools(registry)
        log_server_debug("Registering cube tools...")
        register_cube_tools(registry)
        log_server_debug("Registering vector tools...")
        register_vector_tools(registry)
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

async def _async_main():
    log_server_debug("Executing src/server.py as main module...")
    try:
        log_server_debug(f"Database file location: {os.path.abspath(DB_FILE)}")
        log_server_debug("Calling create_server...")

        server = create_server()

        log_server_debug("Starting StatCan API + DB MCP Server on stdio...")
        # Run using stdio transport
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options()
            )

    except Exception as e:
        log_server_debug(f"UNEXPECTED ERROR in main block: {e}")
        import traceback
        traceback.print_exc(file=sys.stderr)

def main():
    """Sync entry point for the console script."""
    asyncio.run(_async_main())

if __name__ == "__main__":
    main()

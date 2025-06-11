from fastmcp import FastMCP
import os
import sys # Import sys to print to stderr

# Use relative imports within the src package
from .config import DB_FILE
from .api.cube_tools import register_cube_tools
from .api.vector_tools import register_vector_tools
from .api.metadata_tools import register_metadata_tools
from .db.queries import register_db_tools
from .util.logger import log_server_debug 

def create_server(name="StatCanAPI_DB_Server"):
    """Create and configure the MCP server with all tools registered."""
    log_server_debug("Inside create_server function.")
    log_server_debug("Instantiating FastMCP...")
    mcp = FastMCP(name=name)
    log_server_debug("FastMCP instance created.")

    # Register all tools by module
    try:
        log_server_debug("Registering metadata tools...")
        register_metadata_tools(mcp)
        log_server_debug("Registering cube tools...")
        register_cube_tools(mcp)
        log_server_debug("Registering vector tools...")
        register_vector_tools(mcp)
        log_server_debug("Registering db tools...")
        register_db_tools(mcp) # Includes schema tools via queries.py
        log_server_debug("Tool registration complete.")
        
    except Exception as e:
        log_server_debug(f"ERROR during tool registration: {e}")
        # Optionally re-raise or handle differently
        raise

    log_server_debug("Returning mcp instance from create_server.")
    return mcp

# --- Main Execution ---

# This part runs when the script is executed as `python -m src.server`
if __name__ == "__main__":
    log_server_debug("Executing src/server.py as main module...")
    try:
        log_server_debug(f"Database file location: {os.path.abspath(DB_FILE)}")
        log_server_debug("Calling create_server...")
        # Default server instance
        mcp = create_server()
        log_server_debug("Server instance created successfully.")

        log_server_debug("Starting StatCan API + DB MCP Server message...")
        # This print goes to stdout, as intended by the original script
        print("Starting StatCan API + DB MCP Server...")

        log_server_debug("Calling mcp.run()...")
        # This should block and handle the communication loop
        mcp.run()
        # If the script reaches here, mcp.run() finished (unexpectedly?)
        log_server_debug("mcp.run() exited.")

    except Exception as e:
        # Catch any unexpected exceptions during setup or run
        log_server_debug(f"UNEXPECTED ERROR in main block: {e}")
        # Optionally print traceback
        import traceback
        traceback.print_exc(file=sys.stderr)

    finally:
        # This will run even if mcp.run() is interrupted
        log_server_debug("Main execution block finished.")


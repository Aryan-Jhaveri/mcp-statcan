from fastmcp import FastMCP
import os
import sys # Import sys to print to stderr

# Use relative imports within the src package
from .config import DB_FILE
from .api.cube_tools import register_cube_tools
from .api.vector_tools import register_vector_tools
from .api.metadata_tools import register_metadata_tools
from .db.queries import register_db_tools 

def create_server(name="StatCanAPI_DB_Server"):
    """Create and configure the MCP server with all tools registered."""
    print("--> Inside create_server function.", file=sys.stderr) # DEBUG
    print("--> Instantiating FastMCP...", file=sys.stderr) # DEBUG
    mcp = FastMCP(name=name)
    print("--> FastMCP instance created.", file=sys.stderr) # DEBUG

    # Register all tools by module
    try:
        print("--> Registering metadata tools...", file=sys.stderr) # DEBUG
        register_metadata_tools(mcp)
        print("--> Registering cube tools...", file=sys.stderr) # DEBUG
        register_cube_tools(mcp)
        print("--> Registering vector tools...", file=sys.stderr) # DEBUG
        register_vector_tools(mcp)
        print("--> Registering db tools...", file=sys.stderr) # DEBUG
        register_db_tools(mcp) # Includes schema tools via queries.py
        print("--> Tool registration complete.", file=sys.stderr) # DEBUG
    except Exception as e:
        print(f"--> ERROR during tool registration: {e}", file=sys.stderr) # DEBUG
        # Optionally re-raise or handle differently
        raise

    print("--> Returning mcp instance from create_server.", file=sys.stderr) # DEBUG
    return mcp

# --- Main Execution ---

# This part runs when the script is executed as `python -m src.server`
if __name__ == "__main__":
    print("--> Executing src/server.py as main module...", file=sys.stderr) # DEBUG
    try:
        print(f"--> Database file location: {os.path.abspath(DB_FILE)}", file=sys.stderr) # DEBUG
        print("--> Calling create_server...", file=sys.stderr) # DEBUG
        # Default server instance
        mcp = create_server()
        print("--> Server instance created successfully.", file=sys.stderr) # DEBUG

        print("--> Starting StatCan API + DB MCP Server message...", file=sys.stderr) # DEBUG
        # This print goes to stdout, as intended by the original script
        print("Starting StatCan API + DB MCP Server...")

        print("--> Calling mcp.run()...", file=sys.stderr) # DEBUG
        # This should block and handle the communication loop
        mcp.run()
        # If the script reaches here, mcp.run() finished (unexpectedly?)
        print("--> mcp.run() exited.", file=sys.stderr) # DEBUG

    except Exception as e:
        # Catch any unexpected exceptions during setup or run
        print(f"--> UNEXPECTED ERROR in main block: {e}", file=sys.stderr) # DEBUG
        # Optionally print traceback
        import traceback
        traceback.print_exc(file=sys.stderr)

    finally:
        # This will run even if mcp.run() is interrupted
        print("--> Main execution block finished.", file=sys.stderr) # DEBUG


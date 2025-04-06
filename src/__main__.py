"""
Entry point for the StatCan MCP server.

Run this module with `python -m src` to start the server.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

from src.config import LOG_LEVEL, LOG_FILE
from src.server import statcan_server

# Configure logging with error handling
try:
    handlers = [logging.StreamHandler(sys.stderr)]
    
    # Add file handler if path is accessible
    try:
        handlers.append(logging.FileHandler(LOG_FILE))
    except OSError as e:
        print(f"Warning: Could not create log file {LOG_FILE}: {e}", file=sys.stderr)
        print("Logging to console only", file=sys.stderr)
    
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers
    )
except Exception as e:
    print(f"Error setting up logging: {e}", file=sys.stderr)
    # Minimal fallback logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stderr)]
    )

logger = logging.getLogger(__name__)

def main():
    """Run the MCP server."""
    logger.info("Starting StatCan MCP server")
    
    try:
        # FastMCP run method is synchronous and handles everything
        statcan_server.app.run()
    except Exception as e:
        import traceback
        logger.error(f"Error running server: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    logger.info("Starting server via command line")
    main()
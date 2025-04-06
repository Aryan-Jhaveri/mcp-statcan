"""
Entry point for the StatCan MCP server.

Run this module with `python -m src` to start the server.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

import mcp.server.stdio as mcp_stdio

from src.config import LOG_LEVEL, LOG_FILE
from src.server import statcan_server

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr),
        logging.FileHandler(LOG_FILE),
    ]
)

logger = logging.getLogger(__name__)

async def main():
    """Run the MCP server."""
    logger.info("Starting StatCan MCP server")
    
    try:
        # Run with stdio transport
        async with mcp_stdio.stdio_server() as streams:
            await statcan_server.run(
                streams[0],
                streams[1],
                statcan_server.app.create_initialization_options()
            )
    except Exception as e:
        logger.error(f"Error running server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    logger.info("Starting server via command line")
    asyncio.run(main())
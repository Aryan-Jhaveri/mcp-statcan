#!/usr/bin/env python3
"""
Script to run the StatCan MCP server with proper error handling.

Run with: python scripts/run_server.py
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

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

logger = logging.getLogger("mcp-statcan")


async def main():
    """Run the MCP server with proper error handling."""
    logger.info("Starting StatCan MCP server")
    
    try:
        # Run with stdio transport
        async with mcp_stdio.stdio_server() as streams:
            logger.info("Server initialized and waiting for connections")
            await statcan_server.run(
                streams[0],
                streams[1],
                statcan_server.app.create_initialization_options()
            )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Error running server: {e}", exc_info=True)
        return 1
        
    return 0


if __name__ == "__main__":
    print("Starting StatCan MCP Server...")
    print("Press Ctrl+C to stop the server.")
    sys.exit(asyncio.run(main()))
# Statistics Canada API MCP Server

## Description

This project implements a [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that provides tools for interacting with Statistics Canada (StatCan) data APIs. It allows LLMs or other MCP clients to access and retrieve Canadian statistical data in a structured way.

The server is built using the [FastMCP](https://github.com/jlowin/fastmcp) library and interacts with the StatCan Web Data Service via `httpx`.

## Features

This server exposes StatCan API functionalities as MCP tools, including:
* **Cube Operations:**
    * Listing all available data cubes/tables (full and lite versions).
    * Searching cubes by title.
    * Retrieving detailed cube metadata.
    * Getting data for the latest N periods based on ProductId and Coordinate.
    * Getting series info based on ProductId and Coordinate.
    * Getting changed series data based on ProductId and Coordinate.
    * Listing cubes changed on a specific date.
    * Providing download links for full cubes (CSV/SDMX) (Discouraged).
* **Vector Operations:**
    * Retrieving series metadata by Vector ID.
    * Getting data for the latest N periods by Vector ID.
    * Getting data for multiple vectors by reference period range.
    * Getting bulk data for multiple vectors by release date range.
    * Getting changed series data by Vector ID.
    * Listing series changed on a specific date.

*(Refer to the specific tool functions within `src/api/` for detailed parameters and return types.)*

## Project Structure

* **`src/`**: Contains the main source code for the MCP server.
    * **`api/`**: Defines the MCP tools wrapping the StatCan API calls (`cube_tools.py`, `vector_tools.py`, `metadata_tools.py`).
    * **`db/`**: Handles database interactions, including connection, schema, and queries.
    * **`models/`**: Contains Pydantic models for API request/response validation and database representation.
    * **`util/`**: Utility functions (e.g., coordinate padding).
    * **`config.py`**: Configuration loading (e.g., database credentials, API base URL).
    * **`server.py`**: Main FastMCP server definition and tool registration.
    * **`__init__.py`**: Package initialization for `src`.
* **`docs/`**: Contains documentation, particularly text descriptions of the wrapped StatCan API methods.
* **`pyproject.toml` / `uv.lock`**: (Assumed) Project dependency and build configuration.
* **`.env`**: (Assumed) Used for storing sensitive configuration like database credentials, loaded by `src/config.py`.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd attempt7
    ```
2.  **Install Dependencies:** Using [uv](https://github.com/astral-sh/uv) is recommended.
    ```bash
    uv venv  # Create virtual environment (optional but recommended)
    uv pip install -r requirements.txt # Or 'uv sync' if using uv.lock
    # Ensure pyproject.toml lists all dependencies (fastmcp, httpx, pydantic, etc.)
    ```
3.  **Configuration:**
    * Create a `.env` file in the project root (`attempt7/`).
    * Add necessary configuration variables (e.g., database connection details, `STATCAN_API_BASE_URL`) as required by `src/config.py`.

## Running the Server

### Direct Execution (Recommended for Packages)

Run the server as a Python module from the project root directory (`attempt7/`). This ensures relative imports within the `src` package work correctly.

```bash
# Make sure your virtual environment is active
python -m src.server
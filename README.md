# Statistics Canada API MCP Server

## Description

This project implements a [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that provides tools for interacting with Statistics Canada (StatCan) data APIs. It allows LLMs or other MCP clients to access and retrieve Canadian statistical data in a structured way.

The server is built using the [FastMCP](https://github.com/jlowin/fastmcp) library and interacts with the StatCan Web Data Service via `httpx`.

## Claude Chat Examples

| Example | Link | Link | Query |
|---------|------|------|-------|
| Canada's Greenhouse Gas Emissions (2018-2022) | [Source](https://www150.statcan.gc.ca/t1/tbl1/en/cv.action?pid=3810009701) | [View Chat](https://claude.site/artifacts/a1a7e293-3a0b-4b16-9bce-c13a6322ca6b) | "Hey Claude! Can you please create a simple Visualization for green house emissions for Canada as whole over the last 4 years?" |
| Canada's International Trade in Services | [Source](https://www150.statcan.gc.ca/t1/tbl1/en/cv.action?pid=1210014401) | [View Chat](https://claude.site/artifacts/628d9bc2-0d73-41ae-9cff-7235ecf9f0da) | "Hey Claude, Can you create a quick Analysis for International trade in services for the last 6 months. Create a Visualization with key figures please!" |
| Ontario Building Construction Price Index | [Source](https://www150.statcan.gc.ca/t1/tbl1/en/cv.action?pid=1810028901) | [View Chat](https://claude.site/artifacts/efaef40c-7589-4ffd-b3c8-9e82649a2760) | "Hey Claude! can you please generate a visualization for Ontario's Building Price index from Q4 2023 to Q4 2024. Thanks!" |

### Effective Querying Tips

To get the most accurate results from Claude when using this Statistics Canada MCP server:

- **Be Specific**: Use precise, well-formed requests with exact details about the data you need
- **Provide Context**: Clearly specify tables, vectors, time periods, and geographical areas
- **Avoid Typos**: Double-check spelling of statistical terms and place names
- **Structured Questions**: Break complex queries into clear, logical steps
- **Verify Results**: Always cross-check important data against official Statistics Canada sources

> **⚠️ Warning**: LLMs like Claude may occasionally create mock visualizations or fabricate data when unable to retrieve actual information. They might also generate responses with data not available in Statistics Canada to satisfy queries. Always verify results against official sources.

## Features

This server exposes StatCan API functionalities as MCP tools, including:

### API Functionality

* **Cube Operations:**
    * Listing all available data cubes/tables (full and lite versions)
    * Searching cubes by title
    * Retrieving detailed cube metadata
    * Getting data for the latest N periods based on ProductId and Coordinate
    * Getting series info based on ProductId and Coordinate
    * Getting changed series data based on ProductId and Coordinate
    * Listing cubes changed on a specific date
    * Providing download links for full cubes (CSV/SDMX) (Discouraged)
* **Vector Operations:**
    * Retrieving series metadata by Vector ID
    * Getting data for the latest N periods by Vector ID
    * Getting data for multiple vectors by reference period range
    * Getting bulk data for multiple vectors by release date range
    * Getting changed series data by Vector ID
    * Listing series changed on a specific date

### Database Functionality

The server automatically creates a SQLite database (`temp_statcan_data.db`) for:

* Creating tables from API data
* Inserting data into tables
* Querying the database with SQL
* Viewing table schemas and listing available tables

This allows for persistent storage of retrieved data and more complex data manipulation through SQL.

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

### Direct Execution

Run the server as a Python module from the project root directory. This ensures relative imports within the `src` package work correctly.

```bash
# Make sure your virtual environment is active
python -m src.server
```

### Using fastmcp

You can also install and run the server using fastmcp:

```bash
# Install with fastmcp
fastmcp install statcan_mcp_server.py

# Or run directly
python statcan_mcp_server.py
```

### Claude Desktop Configuration

To integrate with Claude Desktop, add this to your `claude_desktop_config.json` (typically in your home directory):

```json
{
  "mcpServers": {
    "StatCanAPI_DB_Server": {
      "command": "uv",
      "args": [
        "run",
        "--with", "fastmcp",
        "--with", "httpx", 
        "sh",
        "-c",
        "cd /Users/aryanjhaveri/Desktop/Projects/mcp-statcan/attempt7 && python -m src.server"
      ]
    }
  }
}
```

Update the path in the `cd` command to match the location of your project directory.

## Known Issues and Limitations

- **SSL Verification**: Currently disabled for development. Should be enabled for production use.
- **Claude Behavior**: May occasionally get stuck in loops or inefficiently make multiple REST calls when a bulk operation would be more efficient.
- **Data Validation**: Always cross-check your data with official Statistics Canada sources.
- **Security Concerns**: Query validation is basic; avoid using with untrusted input.
- **Performance**: Some endpoints may timeout with large data requests.
- **API Rate Limits**: The StatCan API may impose rate limits that affect usage during high-demand periods.

## Usage Examples

### API Operations

```python
# Search for data tables about employment
tables = await search_cubes_by_title("employment")

# Get recent data points for a specific vector ID
data = await get_data_from_vectors_and_latest_n_periods(VectorLatestNInput(vectorId=12345, latestN=5))

# Get data for a specific range of periods
range_data = await get_data_from_vector_by_reference_period_range(
    VectorPeriodRangeInput(vectorId=12345, startDate="2020-01-01", endDate="2020-12-31")
)
```

### Database Operations

```python
# Store API results in SQLite database
create_table_from_data(TableDataInput(table_name="employment_data", data=data))

# Query the database
result = query_database(QueryInput(sql_query="SELECT * FROM employment_data LIMIT 10"))

# List available tables
tables = list_tables()

# Get schema for a table
schema = get_table_schema(TableSchemaInput(table_name="employment_data"))
```
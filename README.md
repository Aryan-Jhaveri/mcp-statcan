[![Statistics Canada MCP Server](assets/StatCan-Header.png)](https://www.statcan.gc.ca/en/start)

# 📊 Statistics Canada API MCP Server

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP](https://img.shields.io/badge/MCP-ModelContextProtocol-green.svg)](https://modelcontextprotocol.io/)
[![GitHub](https://img.shields.io/badge/GitHub-Aryan--Jhaveri-lightgrey?logo=github)](https://github.com/Aryan-Jhaveri)

## 📝 Description

This project implements a [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that provides tools for interacting with Statistics Canada (StatCan) data APIs. It allows LLMs or other MCP clients to access and retrieve Canadian statistical data in a structured way.

The server is built using the [FastMCP](https://github.com/jlowin/fastmcp) library and interacts with the StatCan Web Data Service via `httpx`.

## 📑 Table of Contents

- [📝 Description](#-description)
- [💬 Claude Chat Examples](#-claude-chat-examples)
- [✨ Features](#-features)
- [🏗️ Project Structure](#️-project-structure)
- [📥 Installation](#-installation-guide-for-beginners)
- [🔧 Setup](#-setting-up-claude-desktop-configuration)
- [⚠️ Known Issues](#️-known-issues-and-limitations)
- [🚀 Usage Examples](#-usage-examples)

## 💬 Claude Chat Examples

| Dataset | Query Example | Demo | Data Source |
|---------|--------------|------|------------|
| **Canada's Greenhouse Gas Emissions** (2018-2022) | "Hey Claude! Can you please create a simple visualization for greenhouse emissions for Canada as a whole over the last 4 years?" | [View Demo](https://claude.ai/share/7de892a1-e1d9-410f-96f7-90cd140e5dd9) | [StatCan Table](https://www150.statcan.gc.ca/t1/tbl1/en/cv.action?pid=3810009701) |
| **Canada's International Trade in Services** | "Hey Claude, can you create a quick analysis for international trade in services for the last 6 months. Create a visualization with key figures please!" | [View Demo](https://claude.ai/share/7de892a1-e1d9-410f-96f7-90cd140e5dd9) | [StatCan Table](https://www150.statcan.gc.ca/t1/tbl1/en/cv.action?pid=1210014401) |
| **Ontario Building Construction Price Index** | "Hey Claude! Can you please generate a visualization for Ontario's Building Price index from Q4 2023 to Q4 2024. Thanks!" | [View Demo](https://claude.ai/share/22dee5d0-434e-4270-bb7c-08a86bbe6715) | [StatCan Table](https://www150.statcan.gc.ca/t1/tbl1/en/cv.action?pid=1810028901) |

### Effective Querying Tips

To get the most accurate results from Claude when using this Statistics Canada MCP server:

- **Be Specific**: Use precise, well-formed requests with exact details about the data you need
- **Provide Context**: Clearly specify tables, vectors, time periods, and geographical areas
- **Avoid Typos**: Double-check spelling of statistical terms and place names
- **Structured Questions**: Break complex queries into clear, logical steps
- **Verify Results**: Always cross-check important data against official Statistics Canada sources

> **⚠️ Warning**: LLMs like Claude may occasionally create mock visualizations or fabricate data when unable to retrieve actual information. They might also generate responses with data not available in Statistics Canada to satisfy queries. Always verify results against official sources.

## ✨ Features

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

## 🏗️ Project Structure

* **`src/`**: Contains the main source code for the MCP server.
    * **`api/`**: Defines the MCP tools wrapping the StatCan API calls (`cube_tools.py`, `vector_tools.py`, `metadata_tools.py`).
    * **`db/`**: Handles database interactions, including connection, schema, and queries.
    * **`models/`**: Contains Pydantic models for API request/response validation and database representation.
    * **`util/`**: Utility functions (e.g., coordinate padding).
    * **`config.py`**: Configuration loading (e.g., database credentials, API base URL).
    * **`server.py`**: Main FastMCP server definition and tool registration.
    * **`__init__.py`**: Package initialization for `src`.
* **`pyproject.toml`**: Project dependency and build configuration.
* **`.env`**: (Assumed) Used for storing sensitive configuration like database credentials, loaded by `src/config.py`.

## 📥 Installation Guide for Beginners

If you're new to Python or programming in general, follow these simple steps to get started:

1. **Install Python** (version 3.10 or higher):
   - Download from [python.org](https://www.python.org/downloads/)
   - Make sure to check "Add Python to PATH" during installation

2. **Install uv** (a fast Python package installer):
   ```bash
   # Open your Terminal (Mac/Linux) or Command Prompt (Windows) and run:
   curl -fsSL https://astral.sh/uv/install.sh | bash
   # Or on Windows:
   # curl.exe -fsSL https://astral.sh/uv/install.ps1 -o install.ps1; powershell -ExecutionPolicy Bypass -File install.ps1
   ```

3. **Install fastmcp**:
   ```bash
   uv pip install fastmcp httpx pydantic
   ```

4. **Download this project**:
   ```bash
   git clone https://github.com/Aryan-Jhaveri/mcp-statcan.git
   cd mcp-statcan
   ```

Tip: If you encounter any "module not found" errors, install the missing package with:
```bash
uv pip install package_name
```

## 🔧 Setting Up Claude Desktop Configuration

To integrate with Claude Desktop:

1. **Manually edit the generated config** in your `claude_desktop_config.json`:
   
   Navigate to: Claude Desktop App → Settings (⌘ + ,) → Developer → Edit Config
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
           "cd /path/to/mcp-statcan && python -m src.server"
         ]
       }
     }
   }
   ```

   Replace `/path/to/mcp-statcan` with the absolute path to your project directory. The manual edit is necessary to ensure the server runs with the correct working directory context for proper module resolution.

## ⚠️ Known Issues and Limitations

- **SSL Verification**: Currently disabled for development. Should be enabled for production use.
- **Claude Behavior**: May occasionally get stuck in loops or inefficiently make multiple REST calls when a bulk operation would be more efficient.
- **Data Validation**: Always cross-check your data with official Statistics Canada sources.
- **Security Concerns**: Query validation is basic; avoid using with untrusted input.
- **Performance**: Some endpoints may timeout with large data requests.
- **API Rate Limits**: The StatCan API may impose rate limits that affect usage during high-demand periods.

## 🚀 Usage Examples

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

---

<div align="center">
<p>Made with ❤️ for Statistics Canada data</p>
<p>
<a href="https://github.com/Aryan-Jhaveri/mcp-statcan">GitHub</a> •
<a href="https://github.com/Aryan-Jhaveri/mcp-statcan/issues">Report Bug</a> •
<a href="https://www.statcan.gc.ca/">Statistics Canada</a>
</p>
</div>

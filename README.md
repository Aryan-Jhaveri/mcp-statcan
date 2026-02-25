<a href="https://www.statcan.gc.ca/en/start" target="_blank"><img src="assets/StatCan-Header.png" alt="Statistics Canada MCP Server"></a>

# 📊 Statistics Canada API MCP Server

<a href="https://www.python.org/downloads/" target="_blank"><img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+"></a>
<a href="https://opensource.org/licenses/MIT" target="_blank"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
<a href="https://modelcontextprotocol.io/" target="_blank"><img src="https://img.shields.io/badge/MCP-ModelContextProtocol-green.svg" alt="MCP"></a>
<a href="https://github.com/Aryan-Jhaveri" target="_blank"><img src="https://img.shields.io/badge/GitHub-Aryan--Jhaveri-lightgrey?logo=github" alt="GitHub"></a>

<!-- mcp-name: io.github.Aryan-Jhaveri/mcp-statcan -->

## 📝 Description

This project implements a <a href="https://modelcontextprotocol.io/" target="_blank">Model Context Protocol (MCP)</a> server that provides tools for interacting with Statistics Canada (StatCan) data APIs. 

It allows LLMs or other MCP clients to access and retrieve Canadian statistical data in a structured way.


## 📑 Table of Contents

- [📝 Description](#-description)
- [💬 Claude Chat Examples](#-claude-chat-examples)
- [✨ Features](#-features)
- [🏗️ Project Structure](#️-project-structure)
- [📥 Installation](#-installation)
- [🔧 Setup](#-setting-up-claude-desktop-configuration)
- [⚠️ Known Issues](#️-known-issues-and-limitations)
- [🚀 Usage Examples](#-usage-examples)

## 💬 Claude Chat Examples

| Dataset | Query Example | Demo | Data Source |
|---------|--------------|------|------------|
| **Canada's Greenhouse Gas Emissions** (2018-2022) | "Hey Claude! Can you please create a simple visualization for greenhouse emissions for Canada as a whole over the last 4 years?" | <a href="https://claude.ai/share/7de892a1-e1d9-410f-96f7-90cd140e5dd9" target="_blank">View Demo</a> | <a href="https://www150.statcan.gc.ca/t1/tbl1/en/cv.action?pid=3810009701" target="_blank">StatCan Table</a> |
| **Canada's International Trade in Services** | "Hey Claude, can you create a quick analysis for international trade in services for the last 6 months. Create a visualization with key figures please!" | <a href="https://claude.ai/share/c00eba2d-4e86-4405-878a-7ea4110cb7d3" target="_blank">View Demo</a> | <a href="https://www150.statcan.gc.ca/t1/tbl1/en/cv.action?pid=1210014401" target="_blank">StatCan Table</a> |
| **Ontario Building Construction Price Index** | "Hey Claude! Can you please generate a visualization for Ontario's Building Price index from Q4 2023 to Q4 2024. Thanks!" | <a href="https://claude.ai/share/12ce906f-5a26-4e74-86d9-10451ab5bc4b" target="_blank">View Demo</a> | <a href="https://www150.statcan.gc.ca/t1/tbl1/en/cv.action?pid=1810028901" target="_blank">StatCan Table</a> |


## 📊 Claude Dashboard Example 
| Dataset | Link | Data Source |
|---------|------|------------|
| Labour force characteristics by province, territory and economic region, annual | <a href ="https://claude.ai/public/artifacts/298dfc5f-8e1b-4b73-a4d0-9a68b30cdb54" target="_blank"> Dashbord Link </a> | <a href ="https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1410046401&pickMembers%5B0%5D=2.8&cubeTimeFrame.startYear=2011&cubeTimeFrame.endYear=2025&referencePeriods=20110101%2C20250101" target="_blank"> Data Source </a> |

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

**Cube Operations:**
* Listing all available data cubes/tables — paginated, default 100 per page (`offset`/`limit`)
* Searching cubes by title — capped at `max_results` (default 25) with count message when more exist
* Retrieving cube metadata — `summary=True` (default) caps dimension member lists at 20 entries; use `summary=False` for all vectorIds
* Getting data for the latest N periods based on ProductId and Coordinate
* Getting series info based on ProductId and Coordinate
* Batch-fetching series info for multiple `{productId, coordinate}` pairs in a single call — paginated, with guidance for code-set fields
* Getting changed series data based on ProductId and Coordinate
* Listing cubes changed on a specific date
* Providing download links for full cubes (CSV/SDMX) (Discouraged)

**Vector Operations:**
* Retrieving series metadata by Vector ID
* Getting data for the latest N periods by Vector ID
* Getting data for multiple vectors by reference period range — paginated with guidance
* Getting bulk data for multiple vectors by release date range — paginated with guidance
* Getting changed series data by Vector ID
* Listing series changed on a specific date

**Composite Operations:**
* `fetch_vectors_to_database` — fetches multiple vectors and stores them in SQLite in a single call (preferred workflow for multi-series analysis)

### Database Functionality

The server uses a persistent SQLite database at `~/.statcan-mcp/statcan_data.db` (configurable via `--db-path` flag or `STATCAN_DB_FILE` env var) for:

* Creating tables from API data and inserting rows in one step (`create_table_from_data`)
* Appending additional rows to existing tables (`insert_data_into_table`)
* Querying the database with SQL
* Viewing table schemas and listing available tables

This allows for persistent storage of retrieved data and more complex data manipulation through SQL.

*(Refer to the specific tool functions within `src/api/` for detailed parameters and return types.)*

## 🏗️ Project Structure

* **`src/`**: Contains the main source code for the MCP server.
* **`api/`**: Defines the MCP tools wrapping the StatCan API calls (`cube_tools.py`, `vector_tools.py`, `composite_tools.py`, `metadata_tools.py`).
* **`db/`**: Handles database interactions, including connection, schema, and queries.
* **`models/`**: Contains Pydantic models for API request/response validation and database representation.
* **`util/`**: Utility functions (e.g., coordinate padding).
* **`config.py`**: Configuration loading (e.g., database credentials, API base URL).
* **`server.py`**: Main FastMCP server definition and tool registration.
* **`__init__.py`**: Package initialization for `src`.
* **`pyproject.toml`**: Project dependency and build configuration.
* **`.env`**: (Assumed) Used for storing sensitive configuration like database credentials, loaded by `src/config.py`.

## 📥 Installation

The only requirement is **`uv`**

**macOS/Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows:**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

`uvx` is bundled with `uv` and will automatically download and run `statcan-mcp-server` from PyPI on first use.

## 🔧 Setting Up Claude Desktop Configuration

Navigate to: Claude Desktop App → Settings (⌘ + ,) → Developer → Edit Config

```json
{
  "mcpServers": {
    "statcan": {
      "command": "uvx",
      "args": ["statcan-mcp-server", "--db-path", "/your/path/to/.statcan-mcp/statcan_data.db"]
    }
  }
}
```

> **⚠️ Important:** Pass `--db-path` with an absolute path. Claude Desktop alters the subprocess `HOME` environment variable, which can cause the default database path (`~/.statcan-mcp/`) to resolve incorrectly.

Restart the Claude Desktop app after saving.

### Claude Code

```bash
claude mcp add statcan --scope global -- uvx statcan-mcp-server
```

## ⚠️ Known Issues and Limitations

- **"Unable to open database file" on Claude Desktop**: Pass `--db-path /Users/<you>/.statcan-mcp/statcan_data.db` in your config args (see [Setup](#-setting-up-claude-desktop-configuration)). Claude Desktop alters the subprocess `HOME` env var, breaking default path resolution.
- **SSL Verification**: Currently disabled for development. Should be enabled for production use.
- **Data Validation**: Always cross-check your data with official Statistics Canada sources.
- **Security Concerns**: Query validation is basic; avoid using with untrusted input.
- **Performance**: Some endpoints may timeout with large data requests.
- **API Rate Limits**: The StatCan API may impose rate limits that affect usage during high-demand periods.


<div align="center">
<p>Made with ❤️❤️❤️ for Statistics Canada</p>
<p>
<a href="https://github.com/Aryan-Jhaveri/mcp-statcan" target="_blank">GitHub</a> •
<a href="https://github.com/Aryan-Jhaveri/mcp-statcan/issues" target="_blank">Report Bug</a> •
<a href="https://www.statcan.gc.ca/" target="_blank">Statistics Canada</a>
</p>
</div>

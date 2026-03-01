<a href="https://www.statcan.gc.ca/en/start" target="_blank"><img src="assets/StatCan-Header.png" alt="Statistics Canada MCP Server"></a>

# Statistics Canada MCP Server

<a href="https://www.python.org/downloads/" target="_blank"><img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+"></a>
<a href="https://opensource.org/licenses/MIT" target="_blank"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
<a href="https://modelcontextprotocol.io/" target="_blank"><img src="https://img.shields.io/badge/MCP-ModelContextProtocol-green.svg" alt="MCP"></a>
<a href="https://github.com/Aryan-Jhaveri" target="_blank"><img src="https://img.shields.io/badge/GitHub-Aryan--Jhaveri-lightgrey?logo=github" alt="GitHub"></a>

<!-- mcp-name: io.github.Aryan-Jhaveri/mcp-statcan -->

MCP server for Statistics Canada's [Web Data Service (WDS)](https://www.statcan.gc.ca/eng/developers/wds) and [SDMX REST API](https://www150.statcan.gc.ca/t1/wds/sdmx/statcan/rest/). Gives any MCP client — Claude, ChatGPT, Gemini,Cursor, VS Code Copilot, and more — structured access to Canadian statistical data.

### Currently Hosting!

#### 🚀 Use the hosted version (easiest)
Last Hosting Update:  Feb 28/2026

No installation required, connect to the public server if you the link below works 

**Claude Desktop**
1. Go to **Settings (⌘,) → Connectors → Add Custom Connector**
2. Add mcp-statcan to `name`
3. Add https://mcp-statcan.onrender.com/mcp to `Remote MCP Server URL`
4. Restart Claude Desktop

#### 💻 Can also be Self-host locally (full features and additional SQLite database support, [see below!](#setup-by-client))

#### ️‼️‼️ LLM's may fabricate information, Always double check outputs, see [known issues](#known-issues) below

#### ‼️‼️ Be critical of conclusions and results of analysis done by LLM's, see [known issues](#known-issues) below


#### **Two setup modes:**

| Mode | Tools available | DB/Storage? | Best for |
|---|---|---|---|
| **HTTP** (self-hosted) | WDS + SDMX (~15 tools) | No | Most users — data access without local storage |
| **stdio** (full) | All tools incl. SQLite | Yes | Power users — multi-series analysis, SQL queries |


## Table of Contents

- [Quick Start](#quick-start)
- [Examples](#examples)
- [Setup by Client](#setup-by-client)
- [Features & Tools](#features--tools)
- [Project Structure](#project-structure)
- [Known Issues](#known-issues)

---

## Examples

### Chat demos

| Dataset | Query | Demo | Source |
|---|---|---|---|
| Canada's Greenhouse Gas Emissions (2018-2022) | "Create a simple visualization for greenhouse emissions for Canada as a whole over the last 4 years" | <a href="https://claude.ai/share/7de892a1-e1d9-410f-96f7-90cd140e5dd9" target="_blank">View</a> | <a href="https://www150.statcan.gc.ca/t1/tbl1/en/cv.action?pid=3810009701" target="_blank">Table 38-10-0097-01</a> |
| Canada's International Trade in Services | "Create a quick analysis for international trade in services for the last 6 months with a visualization" | <a href="https://claude.ai/share/c00eba2d-4e86-4405-878a-7ea4110cb7d3" target="_blank">View</a> | <a href="https://www150.statcan.gc.ca/t1/tbl1/en/cv.action?pid=1210014401" target="_blank">Table 12-10-0144-01</a> |
| Ontario Building Construction Price Index | "Generate a visualization for Ontario's Building Price index from Q4 2023 to Q4 2024" | <a href="https://claude.ai/share/12ce906f-5a26-4e74-86d9-10451ab5bc4b" target="_blank">View</a> | <a href="https://www150.statcan.gc.ca/t1/tbl1/en/cv.action?pid=1810028901" target="_blank">Table 18-10-0289-01</a> |

### Dashboard example

| Dataset | Link | Source |
|---|---|---|
| Labour force characteristics by province, territory and economic region, annual | <a href="https://claude.ai/public/artifacts/298dfc5f-8e1b-4b73-a4d0-9a68b30cdb54" target="_blank">Dashboard</a> | <a href="https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1410046401" target="_blank">Table 14-10-0464-01</a> |

---

## Quick Start

Requires [`uv`](https://docs.astral.sh/uv/):

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### HTTP mode — WDS + SDMX, no DB (recommended)

Start the server in a terminal and leave it running:

```bash
uvx statcan-mcp-server --transport http
# Server running at http://localhost:8000  |  /health  |  /mcp
```

Then configure your client to connect to `http://localhost:8000/mcp` — see [Setup by Client](#setup-by-client) below.

### Full mode — add SQLite DB tools

Run via stdio — no separate server process needed:

```bash
uvx statcan-mcp-server
```

Configure your client with the stdio snippets in [Setup by Client](#setup-by-client).

---

## Setup by Client

| Mode | DB tools? | Tools available |
|---|---|---|
| **HTTP** (self-hosted, start server first) | No | WDS + SDMX (~15 tools) |
| **stdio** (full) | Yes | All tools incl. SQLite |

---

### HTTP mode — WDS + SDMX (no DB)

> **Before configuring your client:** start the server in a separate terminal:
> ```bash
> uvx statcan-mcp-server --transport http
> ```
> Keep it running while using your client. Verify at `http://localhost:8000/health`.

Most clients use [`mcp-proxy`](https://github.com/sparfenyuk/mcp-proxy) to bridge stdio ↔ HTTP. Claude Code connects natively.

**Claude Desktop**

Navigate to: Claude Desktop → Settings (⌘,) → Developer → Edit Config

```json
{
  "mcpServers": {
    "statcan": {
      "command": "uvx",
      "args": ["mcp-proxy", "--transport", "streamablehttp", "http://localhost:8000/mcp"]
    }
  }
}
```

Restart Claude Desktop after saving.

**Claude Code**

```bash
claude mcp add statcan --transport http http://localhost:8000/mcp --scope global
```

**Cursor**

In `.cursor/mcp.json` (project) or `~/.cursor/mcp.json` (global):

```json
{
  "mcpServers": {
    "statcan": {
      "command": "uvx",
      "args": ["mcp-proxy", "--transport", "streamablehttp", "http://localhost:8000/mcp"]
    }
  }
}
```

**VS Code (GitHub Copilot)**

In `.vscode/mcp.json`:

```json
{
  "servers": {
    "statcan": {
      "type": "stdio",
      "command": "uvx",
      "args": ["mcp-proxy", "--transport", "streamablehttp", "http://localhost:8000/mcp"]
    }
  }
}
```

**Google Antigravity**

Open the config via the UI: **three dots (⋮) → MCP Servers → Manage MCP Servers → View raw config**, or edit directly:

- macOS / Linux: `~/.gemini/antigravity/mcp_config.json`
- Windows: `C:\Users\<you>\.gemini\antigravity\mcp_config.json`

```json
{
  "mcpServers": {
    "statcan": {
      "command": "uvx",
      "args": ["mcp-proxy", "--transport", "streamablehttp", "http://localhost:8000/mcp"]
    }
  }
}
```

---

### Full mode — WDS + SDMX + SQLite DB tools

No separate server process. `uvx` downloads and runs `statcan-mcp-server` from PyPI automatically.

**Claude Desktop**

Navigate to: Claude Desktop → Settings (⌘,) → Developer → Edit Config

```json
{
  "mcpServers": {
    "statcan": {
      "command": "uvx",
      "args": ["statcan-mcp-server", "--db-path", "/Users/<you>/.statcan-mcp/statcan_data.db"]
    }
  }
}
```

> **Note:** Pass `--db-path` with an absolute path. Claude Desktop overrides the subprocess `HOME` env var, which breaks the default `~/.statcan-mcp/` path resolution.

Restart Claude Desktop after saving.

**Claude Code**

```bash
claude mcp add statcan --scope global -- uvx statcan-mcp-server
```

**Cursor**

In `.cursor/mcp.json` (project) or `~/.cursor/mcp.json` (global):

```json
{
  "mcpServers": {
    "statcan": {
      "command": "uvx",
      "args": ["statcan-mcp-server"]
    }
  }
}
```

**VS Code (GitHub Copilot)**

In `.vscode/mcp.json`:

```json
{
  "servers": {
    "statcan": {
      "type": "stdio",
      "command": "uvx",
      "args": ["statcan-mcp-server"]
    }
  }
}
```

**Google Antigravity**

Open the config via the UI: **three dots (⋮) → MCP Servers → Manage MCP Servers → View raw config**, or edit directly:

- macOS / Linux: `~/.gemini/antigravity/mcp_config.json`
- Windows: `C:\Users\<you>\.gemini\antigravity\mcp_config.json`

```json
{
  "mcpServers": {
    "statcan": {
      "command": "uvx",
      "args": ["statcan-mcp-server"]
    }
  }
}
```

**Optional flags (full/stdio mode)**

```bash
# Custom database path (recommended for Claude Desktop)
uvx statcan-mcp-server --db-path /your/path/statcan_data.db

# Environment variable alternative
STATCAN_DB_FILE=/your/path/statcan_data.db uvx statcan-mcp-server
```

---

## Features & Tools

### SDMX Tools — recommended for data fetching

Server-side filtered observations. Only the requested slice is returned — no downloading full tables.

| Tool | Description |
|---|---|
| `get_sdmx_structure` | Fetch dimension codelists + key syntax for a table. Call this before `get_sdmx_data`. |
| `get_sdmx_data` | Fetch filtered observations by `productId` + `key`. Supports `lastNObservations`, `startPeriod`, `endPeriod`. |
| `get_sdmx_vector_data` | Fetch observations for a single vectorId via SDMX. |

**Key syntax** (passed to `get_sdmx_data`):
- `"1.2.1"` — Geography=1, Gender=2, Age=1
- `".2.1"` — all geographies (wildcard), Gender=2, Age=1
- `lastNObservations=12` — last 12 periods (e.g. 1 year of monthly data)
- Limitation: `lastNObservations` cannot combine with `startPeriod`/`endPeriod` (StatCan returns 406)

### WDS Discovery & Metadata

| Tool | Description |
|---|---|
| `search_cubes_by_title` | Full-text search across all StatCan tables. AND logic on multiple keywords, capped at 25 results. |
| `get_all_cubes_list` | Paginated table inventory with dimension details (`offset`/`limit`, default 100/page). |
| `get_all_cubes_list_lite` | Same but lighter — no dimension or footnote info. |
| `get_cube_metadata` | Dimension info, member lists, date ranges. `summary=True` (default) caps members at 10 per dimension. |
| `get_code_sets` | Decode StatCan numeric codes (frequency, UOM, scalar factor, status). |

### WDS Series Resolution

| Tool | Description |
|---|---|
| `get_series_info` | Resolve one or more `{productId, coordinate}` pairs to vectorId + metadata in a single call. Replaces the old single + bulk coord tools. |
| `get_series_info_from_vector` | Resolve a vectorId to productId, coordinate, titles, frequency. |

### WDS Change Detection

| Tool | Description |
|---|---|
| `get_changed_cube_list` | Tables updated on a specific date (YYYY-MM-DD). |
| `get_changed_series_list` | Series updated on a specific date. |
| `get_changed_series_data_from_cube_pid_coord` | Data points that changed for a coordinate. |
| `get_changed_series_data_from_vector` | Data points that changed for a vectorId. |

### WDS Data Fetch

| Tool | Description |
|---|---|
| `get_bulk_vector_data_by_range` | Fetch multiple vectors filtered by **release date** range (YYYY-MM-DDTHH:MM). Use when you want "data released between date A and date B", not a reference period range. |

### Composite Tools *(local/stdio mode only)*

| Tool | Description |
|---|---|
| `fetch_vectors_to_database` | Fetch multiple vectors by reference period range and store to SQLite in one call. Preferred workflow for multi-series analysis. |
| `store_cube_metadata` | Fetch full cube metadata and store into `_statcan_dimensions` + `_statcan_members` tables. Use SQL to browse all members and look up vectorIds without loading them into context. |

### Database Tools *(local/stdio mode only)*

Persistent SQLite at `~/.statcan-mcp/statcan_data.db`.

| Tool | Description |
|---|---|
| `create_table_from_data` | Create a table and insert rows in one step. |
| `insert_data` | Append rows to an existing table. |
| `query_database` | Read-only SQL (`PRAGMA query_only = ON`). |
| `list_tables` | List all tables. |
| `get_table_schema` | Schema for a table. |
| `drop_table` | Drop a table. |

---

### Typical workflow (local mode)

```
1. search_cubes_by_title("unemployment rate")
   → find productId, e.g. 14100287

2. get_sdmx_structure(productId=14100287)
   → see dimensions + codes for key construction

3. get_sdmx_data(productId=14100287, key=".2.1", lastNObservations=24)
   → last 24 months, all geographies, seasonally adjusted

4. (optional) get_series_info(items=[{productId:14100287, coordinate:"1.2.1"}])
   → get vectorId for a specific series

5. (optional) fetch_vectors_to_database(vectorIds=[...], table_name="unemployment")
   → store for SQL analysis
```

> **Warning:** LLMs may occasionally fabricate data when unable to retrieve actual information. Always verify important figures against [official Statistics Canada sources](https://www.statcan.gc.ca/).

---

## Project Structure

```
src/
├── api/
│   ├── cube_tools.py        # WDS cube + search tools
│   ├── vector_tools.py      # WDS vector tools
│   ├── sdmx_tools.py        # SDMX REST tools
│   ├── composite_tools.py   # fetch_vectors_to_database, store_cube_metadata
│   └── metadata_tools.py    # get_code_sets
├── db/                      # SQLite connection, schema, queries
├── models/                  # Pydantic input models
├── util/
│   ├── registry.py          # ToolRegistry — @decorator → MCP Tool schema
│   ├── truncation.py        # Response truncation + pagination guidance
│   ├── sdmx_json.py         # SDMX-JSON → tabular rows
│   ├── cache.py             # 1-hour TTL cache for cube list
│   └── coordinate.py        # Pad WDS coordinate to 10 dimensions
├── config.py                # BASE_URL, SDMX_BASE_URL, DB_FILE, TRANSPORT, PORT
└── server.py                # create_server(), transport wiring, CLI entrypoint
```

---

## Known Issues

- **"Unable to open database file" on Claude Desktop**: Pass `--db-path /Users/<you>/.statcan-mcp/statcan_data.db` in your config (see [Setup](#claude-desktop)). Claude Desktop overrides the subprocess `HOME` env var.
- **SSL verification disabled**: `VERIFY_SSL = False` in all StatCan API calls. This is a known limitation — StatCan's certificate chain causes verification failures in some environments.
- **SDMX OR-key geography labels**: Using `+` syntax for multiple geographies (e.g. `"1+2.2.1"`) produces incorrect Geography labels for series 2+. Use wildcard (omit the dimension: `".2.1"`) instead — this is a StatCan API bug.
- **`lastNObservations` + date range**: StatCan SDMX returns 406 when combining `lastNObservations` with `startPeriod`/`endPeriod`. Use one or the other.
- **Context overflow may cause data fabrication**: When tool results are large, the LLM's context window fills up and it may fabricate or hallucinate data values instead of fetching them. Always verify important figures against [official Statistics Canada sources](https://www.statcan.gc.ca/). Use precise SDMX queries (`lastNObservations`, specific keys) to keep responses small.
- **Rate limits**: StatCan's API may throttle during high-demand periods.

---
<div align="center"> Made with ❤️❤️❤️ for Statistics Canada </div>

<div align="center">
<p>
<a href="https://github.com/Aryan-Jhaveri/mcp-statcan" target="_blank">GitHub</a> •
<a href="https://github.com/Aryan-Jhaveri/mcp-statcan/issues" target="_blank">Report Bug</a> •
<a href="https://www.statcan.gc.ca/" target="_blank">Statistics Canada</a>
</p>
</div>

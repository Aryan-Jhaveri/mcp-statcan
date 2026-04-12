<a href="https://www.statcan.gc.ca/en/start" target="_blank"><img src="assets/StatCan-Header.jpg" alt="Statistics Canada MCP Server"></a>

# Statistics Canada MCP Server

<a href="https://www.python.org/downloads/" target="_blank"><img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+"></a>
<a href="https://opensource.org/licenses/MIT" target="_blank"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
<a href="https://modelcontextprotocol.io/" target="_blank"><img src="https://img.shields.io/badge/MCP-ModelContextProtocol-green.svg" alt="MCP"></a>
<a href="https://github.com/Aryan-Jhaveri" target="_blank"><img src="https://img.shields.io/badge/GitHub-Aryan--Jhaveri-lightgrey?logo=github" alt="GitHub"></a>
[![SafeSkill 93/100](https://img.shields.io/badge/SafeSkill-93%2F100_Verified%20Safe-brightgreen)](https://safeskill.dev/scan/aryan-jhaveri-mcp-statcan)

<!-- mcp-name: io.github.Aryan-Jhaveri/mcp-statcan -->

MCP server and CLI for Statistics Canada's [Web Data Service (WDS)](https://www.statcan.gc.ca/eng/developers/wds) and [SDMX REST API](https://www150.statcan.gc.ca/t1/wds/sdmx/statcan/rest/). Gives any MCP client — Claude, Cursor, VS Code Copilot, Gemini — structured access to Canadian statistical data. Includes a standalone `statcan` CLI for direct downloads without an LLM.

> **Hosted on Render — no install required for most users. See [Quick Start](#quick-start).**

**⚠️ LLMs may fabricate data. Always verify important figures against [official Statistics Canada sources](https://www.statcan.gc.ca/).**

---

## Table of Contents

- [Quick Start](#quick-start)
- [Examples](#examples)
- [Setup by Client](#setup-by-client)
- [How Claude.ai Uses This Server](#how-claudeai-uses-this-server)
- [MCP Prompts](#mcp-prompts)
- [statcan CLI](#statcan-cli)
- [Features & Tools](#features--tools)
- [Project Structure](#project-structure)
- [Known Issues](#known-issues)

---

## Quick Start

Pick the option that fits you. You don't need to install anything for Option 1.

### Option 1 — Use the hosted server (recommended)

Connect directly to the public server on Render. No `uv`, no terminal, no local setup.

**Claude Desktop / Claude.ai**
1. Open **Settings → Connectors → Add Custom Connector**
2. Name: `mcp-statcan`
3. URL: `https://mcp-statcan.onrender.com/mcp`
4. Save and restart

**Claude Code**
```bash
claude mcp add statcan --transport http https://mcp-statcan.onrender.com/mcp --scope global
```

> The hosted server provides all WDS + SDMX tools. Database tools (SQLite) require local setup (Option 3) — they are intentionally excluded from the shared server.

---

### Option 2 — Self-host HTTP (WDS + SDMX, no DB)

Run a local server with the same tools as the hosted version.

**Step 1** — Install [`uv`](https://docs.astral.sh/uv/):
```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Step 2** — Start the server:
```bash
uvx statcan-mcp-server --transport http
# Listening at http://localhost:8000
```

**Step 3** — Connect your client to `http://localhost:8000/mcp`.

---

### Option 3 — Full local setup (WDS + SDMX + SQLite)

Everything from Option 2, plus database tools for storing and querying data with SQL. Runs via stdio.

**Step 1** — Install `uv` (same as above).

**Step 2** — Configure your client with the stdio snippets in [Setup by Client](#setup-by-client) below.

`uvx` downloads and runs the server automatically on first use.

---

### Option 4 — `statcan` CLI (no LLM needed)

Download StatCan data directly from the terminal. See [statcan CLI](#statcan-cli).

```bash
uvx statcan-mcp-server        # installs the package
statcan search "labour force"
statcan download 14-10-0287-01 --last 12 --output lfs.csv
```

---

## Examples

### Chat examples

| Dataset | Query | Demo | Source |
|---|---|---|---|
| Canada's Greenhouse Gas Emissions | "Create a simple visualization for greenhouse emissions for Canada as a whole over the last 4 years" | <a href="https://claude.ai/share/7de892a1-e1d9-410f-96f7-90cd140e5dd9" target="_blank">Chat</a> | <a href="https://www150.statcan.gc.ca/t1/tbl1/en/cv.action?pid=3810009701" target="_blank">Table 38-10-0097-01</a> |
| Canada's International Trade in Services | "Create a quick analysis for international trade in services for the last 6 months with a visualization" | <a href="https://claude.ai/share/c00eba2d-4e86-4405-878a-7ea4110cb7d3" target="_blank">Chat</a> | <a href="https://www150.statcan.gc.ca/t1/tbl1/en/cv.action?pid=1210014401" target="_blank">Table 12-10-0144-01</a> |
| Ontario Building Construction Price Index | "Generate a visualization for Ontario's Building Price index from Q4 2023 to Q4 2024" | <a href="https://claude.ai/share/12ce906f-5a26-4e74-86d9-10451ab5bc4b" target="_blank">Chat</a> | <a href="https://www150.statcan.gc.ca/t1/tbl1/en/cv.action?pid=1810028901" target="_blank">Table 18-10-0289-01</a> |
| Canadian Unemployment Dashboard | "Create a Canadian Unemployment Dashboard using statcan mcp" | <a href="https://claude.ai/share/50d72d90-ec98-463e-88ec-85032edc9c29" target="_blank">Chat</a> | <a href="https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1410028701&pickMembers%5B0%5D=1.1&pickMembers%5B1%5D=3.1&pickMembers%5B2%5D=4.1&pickMembers%5B3%5D=5.1&cubeTimeFrame.startMonth=04&cubeTimeFrame.startYear=2023&cubeTimeFrame.endMonth=03&cubeTimeFrame.endYear=2026&referencePeriods=20230401%2C20260301" target="_blank">Table 14-10-0287-01</a> |

### Dashboard examples

| Title | Link | Source |
|---|---|---|
| Canada's Critical Minerals Economy | <a href="https://claude.ai/public/artifacts/15d289c7-f324-4ced-bcc0-53d6ac3218c9" target="_blank">Dashboard</a> | <a href="https://www150.statcan.gc.ca/t1/tbl1/en/cv.action?pid=3610070801" target="_blank">Table 36-10-0708-01</a> |
| Price of Everything: CPI Dashboard 2015–2026 | <a href="https://claude.ai/public/artifacts/61e99645-934c-4fe2-9693-88dca714a634" target="_blank">Dashboard</a> | <a href="https://www150.statcan.gc.ca/t1/tbl1/en/cv.action?pid=1810000401" target="_blank">Table 18-10-0004-01</a> |
| Canada's Biomedical & Biotech Industries | <a href="https://claude.ai/public/artifacts/749ab9ef-c7a2-4186-8a75-d94a6eb8772e" target="_blank">Dashboard</a> | <a href="https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=2710029701" target="_blank">Table 27-10-0297-01</a> |

---

## Setup by Client

### Hosted server (Option 1)

**Claude Desktop** — Settings → Connectors → Add Custom Connector
- Name: `mcp-statcan`
- URL: `https://mcp-statcan.onrender.com/mcp`

**Claude Code**
```bash
claude mcp add statcan --transport http https://mcp-statcan.onrender.com/mcp --scope global
```

**Cursor** — `.cursor/mcp.json` (project) or `~/.cursor/mcp.json` (global):
```json
{
  "mcpServers": {
    "statcan": {
      "url": "https://mcp-statcan.onrender.com/mcp"
    }
  }
}
```

**VS Code (GitHub Copilot)** — `.vscode/mcp.json`:
```json
{
  "servers": {
    "statcan": {
      "type": "http",
      "url": "https://mcp-statcan.onrender.com/mcp"
    }
  }
}
```

---

### Self-hosted HTTP (Option 2)

> Start `uvx statcan-mcp-server --transport http` first, then configure your client.

Most clients need [`mcp-proxy`](https://github.com/sparfenyuk/mcp-proxy) to bridge stdio ↔ HTTP. Claude Code connects natively.

**Claude Desktop** — Settings → Developer → Edit Config:
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

**Claude Code**
```bash
claude mcp add statcan --transport http http://localhost:8000/mcp --scope global
```

**Cursor / VS Code / Gemini** — same `mcp-proxy` wrapper, pointing to `http://localhost:8000/mcp`.

---

### Full local / stdio (Option 3)

**Claude Desktop** — Settings → Developer → Edit Config:
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
> Pass `--db-path` with an absolute path. Claude Desktop overrides the subprocess `HOME` env var, which can break default path resolution.

**Claude Code**
```bash
claude mcp add statcan --scope global -- uvx statcan-mcp-server
```

**Cursor / VS Code / Gemini** — use `uvx statcan-mcp-server` as the stdio command.

---

## How Claude.ai Uses This Server

Claude.ai (web) has no bash sandbox — it can't run shell commands. Instead, it uses MCP tools for discovery and its **Python script tool** to fetch data without bloating the context window.

**The pattern:**

```
1. MCP tools (small payloads — metadata only):
   search_cubes_by_title("labour force")  → productId
   get_sdmx_structure(productId=...)      → dimension layout + codes
   get_sdmx_key_for_dimension(...)        → OR key for large dimensions

2. Python script (data never enters context):
   url = "https://mcp-statcan.onrender.com/files/sdmx/<pid>/<key>?lastNObservations=12"
   → validate URL domain → write to ./statcan_<pid>.csv → print summary only

3. Follow-up script (analysis from local file):
   rows = list(csv.DictReader(open("./statcan_<pid>.csv")))
   → filter / sort / aggregate → print only the result
```

`get_sdmx_data` on the hosted server always returns a `download_csv` URL instead of inline data — data stays out of the context window regardless of response size.

**Claude Code (bash sandbox)** uses the `statcan` CLI instead:

```bash
statcan search "labour force"
statcan download 14-10-0287-01 --last 12 --output ./lfs.csv
awk -F',' 'NR>1 && $1=="Canada"' ./lfs.csv | sort -t',' -rn -k5 | head -10
```

---

## MCP Prompts

The server ships five prompts accessible as slash commands in supported clients. Each has dual instructions — Claude Code (bash) and Claude.ai web (Python script).

| Prompt | What it teaches |
|---|---|
| `/statcan-data-lookup` | End-to-end: search → structure → build key → fetch to local file → analyze |
| `/sdmx-key-builder` | SDMX key syntax: wildcards, OR keys, time parameters, download URL format |
| `/statcan-download` | Download a specific table: CLI commands + Python script alternative |
| `/statcan-explore` | Sample before committing: 3-period fetch, column layout, size estimate |
| `/statcan-vector-pipeline` | Multi-series download and cross-series comparison |

**Usage in Claude Code:**
```
/statcan-data-lookup topic="consumer price index" analysis_goal="trend last 5 years"
/statcan-download product_id=18100004 last_n=24
```

---

## statcan CLI

A standalone CLI for downloading StatCan data without an LLM. Outputs pipe-friendly CSV/JSON to stdout; progress and errors go to stderr.

**Install:**
```bash
pip install statcan-mcp-server   # or: uvx statcan-mcp-server (no install)
```

**Commands:**

```
statcan search <term>            Search tables by keyword
statcan metadata <product-id>    Show table structure (dimensions + members)
statcan download <product-id>    Download observations via SDMX
statcan vector <vector-id>...    Download one or more vector series
statcan codeset                  Show StatCan code definitions (UOM, frequency, etc.)
```

**Common usage:**

```bash
# Find a table
statcan search "consumer price index"
statcan search "labour force" --max-results 10 --format json

# Inspect structure before downloading
statcan metadata 18-10-0004-01
statcan metadata 18100004 --full        # show all dimension members

# Download data
statcan download 18-10-0004-01 --last 12 --output cpi.csv
statcan download 18-10-0004-01 --key "1.1.1" --start 2020-01 --end 2024-12
statcan download 18-10-0004-01 --last 5 --dry-run   # preview SDMX URL

# Download by vector ID
statcan vector v41690973 --last 24 --output series.csv
statcan vector v41690973 v41690974 --last 12 --output multi.csv

# Decode numeric codes
statcan codeset --type uom
statcan codeset --type frequency --format json
```

**Output formats:** `csv` (default for download/vector), `table` (default for search/metadata/codeset), `json`

**Pipe patterns:**
```bash
# Top 10 by value
statcan download 14-10-0287-01 --last 1 --format csv \
  | awk -F',' 'NR>1' | sort -t',' -k5 -rn | head -10

# Extract unique geographies
statcan download 14-10-0287-01 --last 1 --format csv \
  | awk -F',' 'NR>1 {print $1}' | sort -u

# Chain search → download
PID=$(statcan search "CPI" --format json | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['Product ID'])")
statcan download $PID --last 12 --output cpi.csv
```

For the complete CLI reference see [cli.md](cli.md).

---

## Features & Tools

### SDMX Tools — server-side filtered data fetch

Only the slice you request is returned. No downloading full tables.

| Tool | Description |
|---|---|
| `get_sdmx_structure` | Dimension codelists + key syntax for a table. Call before `get_sdmx_data`. |
| `get_sdmx_data` | Filtered observations by `productId` + key. Returns a CSV download URL on the hosted server — data stays out of context. |
| `get_sdmx_vector_data` | Observations for a single vectorId via SDMX. |
| `get_sdmx_key_for_dimension` | All leaf member IDs for a large dimension as a ready-to-paste OR key. Use when a dimension has >30 codes (e.g. NOC, CMAs). |

**Key syntax** (passed to `get_sdmx_data`):
- `"1.2.1"` — Geography=1, Gender=2, Age=1
- `".2.1"` — all geographies (wildcard), Gender=2, Age=1
- `"1+2.2.1"` — Geography 1 or 2, Gender=2, Age=1

> **Note:** Wildcard (`.`) on dimensions with >30 codes returns a sparse, unpredictable sample. Use `get_sdmx_key_for_dimension` to get the correct OR key.

### WDS Discovery & Metadata

| Tool | Description |
|---|---|
| `search_cubes_by_title` | Full-text search across all StatCan tables. AND logic, capped at 25 results. |
| `get_all_cubes_list` / `_lite` | Paginated table inventory (`offset`/`limit`, default 100/page). |
| `get_cube_metadata` | Dimension info, member lists, date ranges. `summary=True` caps members at 10 per dimension. |
| `get_code_sets` | Decode StatCan numeric codes (frequency, UOM, scalar factor, status). |

### WDS Series Resolution & Change Detection

| Tool | Description |
|---|---|
| `get_series_info` | Resolve `{productId, coordinate}` pairs to vectorId + metadata. |
| `get_series_info_from_vector` | Resolve a vectorId to productId, coordinate, titles, frequency. |
| `get_changed_cube_list` | Tables updated on a specific date. |
| `get_changed_series_list` | Series updated on a specific date. |
| `get_changed_series_data_from_cube_pid_coord` | Data points that changed for a coordinate. |
| `get_changed_series_data_from_vector` | Data points that changed for a vectorId. |
| `get_bulk_vector_data_by_range` | Multiple vectors filtered by release date range. |

### Composite & Database Tools *(local/stdio mode only)*

These tools are not available on the hosted Render server — SQLite is per-process and not shared across users.

| Tool | Description |
|---|---|
| `fetch_vectors_to_database` | Fetch vectors by reference period range and store to SQLite. |
| `store_cube_metadata` | Fetch full cube metadata into SQLite — browse all members and vectorIds with SQL. |
| `query_database` | Read-only SQL against the local SQLite database. |
| `create_table_from_data` / `insert_data` | Create or append to a table. |
| `list_tables` / `get_table_schema` / `drop_table` | Database utilities. |

### Typical workflow

**Claude.ai web (hosted server):**
```
1. search_cubes_by_title("unemployment rate")
   → productId e.g. 14100287

2. get_sdmx_structure(productId=14100287)
   → dimension positions + sample codes

3. get_sdmx_key_for_dimension(productId=14100287, dimension_position=3)
   → or_key for large dimensions

4. get_sdmx_data(productId=14100287, key=".2.1", lastNObservations=24)
   → returns download_csv URL

5. Python script: validate URL domain → write to ./statcan_14100287.csv → analyze → print summary
```

**Claude Code (bash sandbox):**
```bash
statcan search "unemployment rate"
statcan metadata 14100287
statcan download 14-10-0287-01 --last 24 --output ./lfs.csv
awk -F',' 'NR>1 && $1=="Canada"' ./lfs.csv | sort -t',' -rn -k5 | head -10
```

---

## Project Structure

```
src/
├── api/
│   ├── cube/
│   │   ├── discovery.py         # search_cubes_by_title, get_all_cubes_list
│   │   ├── metadata.py          # get_cube_metadata
│   │   └── series.py            # get_series_info, change detection
│   ├── vector/
│   │   └── vector_tools.py      # vector series, bulk range fetch
│   ├── sdmx/
│   │   └── sdmx_tools.py        # get_sdmx_structure, get_sdmx_data, get_sdmx_key_for_dimension
│   ├── composite_tools.py       # fetch_vectors_to_database, store_cube_metadata (stdio only)
│   └── metadata_tools.py        # get_code_sets
├── cli/
│   ├── main.py                  # statcan CLI entry point (Typer app)
│   ├── output.py                # write_output, format helpers
│   └── commands/
│       ├── search.py            # statcan search
│       ├── metadata.py          # statcan metadata
│       ├── download.py          # statcan download
│       ├── vector.py            # statcan vector
│       └── codeset.py           # statcan codeset
├── db/                          # SQLite connection, schema, queries (stdio only)
├── models/                      # Pydantic input models
├── util/
│   ├── registry.py              # ToolRegistry — @decorator → MCP Tool schema
│   ├── truncation.py            # Response truncation + pagination guidance
│   ├── sdmx_json.py             # SDMX-JSON → tabular rows
│   └── cache.py                 # 1-hour TTL cache for cube list
├── config.py                    # BASE_URL, SDMX_BASE_URL, RENDER_BASE_URL, TRANSPORT, PORT
└── server.py                    # create_server(), MCP Prompts, HTTP routes (/files/sdmx/), CLI
```

---

## Known Issues

| Issue | Status | Workaround |
|---|---|---|
| **"Unable to open database file" on Claude Desktop** | Active | Pass `--db-path /Users/<you>/.statcan-mcp/statcan_data.db` in your config |
| **SSL verification disabled** | Active | `VERIFY_SSL = False` in all API calls — StatCan cert issues made this necessary |
| **`lastNObservations` + `startPeriod`/`endPeriod` → 406** | Active | Use one or the other, not both |
| **OR syntax for Geography dimension unreliable** | Active | Use wildcard (`.`) for Geography; OR works fine for other dimensions |
| **Wildcard returns sparse data for large dimensions** | Mitigated | Use `get_sdmx_key_for_dimension` to get the full OR key (e.g. NOC, CMAs) |
| **Context overflow may cause data fabrication** | Mitigated | Hosted server returns `download_csv` URL — data processed via script, not context |

---

<div align="center">Made with ❤️❤️❤️ for Statistics Canada</div>

<div align="center">
<a href="https://github.com/Aryan-Jhaveri/mcp-statcan" target="_blank">GitHub</a> •
<a href="https://github.com/Aryan-Jhaveri/mcp-statcan/issues" target="_blank">Report Bug</a> •
<a href="https://www.statcan.gc.ca/" target="_blank">Statistics Canada</a>
</div>

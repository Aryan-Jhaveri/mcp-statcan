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
- [Contributors](#contributors)

---

## Quick Start

Pick the option that fits you. You don't need to install anything for Option 1.

### Option 1 — Use the hosted server (recommended)

Connect directly to the public server on Render. No `uv`, no terminal, no local setup.

**Claude Desktop / Claude.ai**
1. Open **Settings → Connectors → Add Custom Connector**
2. Name: `mcp-statcan`
3. URL: `https://mcp-statcan.com/mcp`
4. Save and restart

**Claude Code**
```bash
claude mcp add statcan --transport http https://mcp-statcan.com/mcp --scope global
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
statcan metadata 14-10-0287-01                                    # run first to find dimension IDs
statcan download 14-10-0287-01 --key "1.1.1" --last 12 --output lfs.csv  # run `statcan metadata <pid>` first to find real dimension IDs
statcan describe                                                  # machine-readable command reference for agents
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
- URL: `https://mcp-statcan.com/mcp`

**Claude Code**
```bash
claude mcp add statcan --transport http https://mcp-statcan.com/mcp --scope global
```

**Cursor** — `.cursor/mcp.json` (project) or `~/.cursor/mcp.json` (global):
```json
{
  "mcpServers": {
    "statcan": {
      "url": "https://mcp-statcan.com/mcp"
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
      "url": "https://mcp-statcan.com/mcp"
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
   url = "https://mcp-statcan.com/files/sdmx/<pid>/<key>?lastNObservations=12"
   → validate URL domain → write to ./statcan_<pid>.csv → print summary only

3. Follow-up script (analysis from local file):
   rows = list(csv.DictReader(open("./statcan_<pid>.csv")))
   → filter / sort / aggregate → print only the result
```

For questions that need computation (rank, compare, growth), `query_sdmx` runs the SQL on the server and returns only the answer, so raw rows never enter the context window.

**Claude Code (bash sandbox)** uses the `statcan` CLI instead:

```bash
statcan search "labour force"
statcan metadata 14-10-0287-01  # run first to find dimension IDs
statcan download 14-10-0287-01 --key "1.1.1" --last 12 --output ./lfs.csv  # run `statcan metadata <pid>` first to find real dimension IDs
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

**Exploring a table** (search, then metadata, then download):

<img src="assets/cli-explore.gif" alt="Terminal recording: statcan search, statcan metadata and statcan download for the Consumer Price Index table" width="800">

**Agent mode** (`--json` envelopes, typed exit codes, `statcan describe`):

<img src="assets/cli-agent.gif" alt="Terminal recording: statcan --json download writes a CSV and prints a summary envelope; a missing product returns a JSON error with exit code 3; statcan describe lists exit codes" width="800">

Recordings are generated from the scripts in [`assets/tapes/`](assets/tapes/) with [VHS](https://github.com/charmbracelet/vhs): `vhs assets/tapes/cli-agent.tape`.

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
statcan describe                 Commands, options, exit codes and JSON envelopes as JSON
```

**Common usage:**

```bash
# Find a table
statcan search "consumer price index"
statcan search "labour force" --max-results 10 --format json

# Inspect structure before downloading
statcan metadata 18-10-0004-01
statcan metadata 18100004 --full        # show all dimension members

# Download data (run `statcan metadata <pid>` first to find real dimension IDs)
statcan download 18-10-0004-01 --key "1.1.1" --last 12 --output cpi.csv
statcan download 18-10-0004-01 --key "1.1.1" --start 2020-01 --end 2024-12
statcan download 18-10-0004-01 --key "1.1.1" --last 5 --dry-run   # preview SDMX URL

# Download by vector ID
statcan vector v41690973 --last 24 --output series.csv
statcan vector v41690973 v41690974 --last 12 --output multi.csv

# Decode numeric codes
statcan codeset --type uom
statcan codeset --type frequency --format json
```

**Output formats:** `csv` (default for download/vector), `table` (default for search/metadata/codeset), `json`, `ndjson`

**For agents and scripts:** put `--json` before the subcommand (or set `STATCAN_OUTPUT=json`) to get one JSON envelope on stdout, JSON errors with a `hint` on stderr, and stable exit codes (`0` ok, `2` usage, `3` not found, `4` rejected, `5` retryable, `6` empty). With `--output`, the envelope summarizes the file (rows, columns, period range, series count) so it never has to be read back. Details: [machine-readable mode](src/cli/README.md#machine-readable-mode-agents-and-scripts).

**Pipe patterns:**
```bash
# Top 10 by value (run `statcan metadata <pid>` first to find real dimension IDs)
statcan download 14-10-0287-01 --key "1.1.1" --last 1 --format csv \
  | awk -F',' 'NR>1' | sort -t',' -k5 -rn | head -10

# Extract unique geographies (run `statcan metadata <pid>` first to find real dimension IDs)
statcan download 14-10-0287-01 --key "1.1.1" --last 1 --format csv \
  | awk -F',' 'NR>1 {print $1}' | sort -u

# Chain search → download (run `statcan metadata <pid>` first to find real dimension IDs)
PID=$(statcan search "CPI" --format json | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['Product ID'])")
statcan download $PID --key "1.1.1" --last 12 --output cpi.csv
```

For the complete CLI reference see [src/cli/README.md](src/cli/README.md).

---

## Features & Tools

### SDMX Tools — server-side filtered data fetch

Only the slice you request is returned. No downloading full tables.

| Tool | Description |
|---|---|
| `get_sdmx_structure` | Dimension codelists + key syntax for a table. Call before `get_sdmx_data`. |
| `get_sdmx_data` | Filtered observations by `productId` + key, returned inline (capped at 500 rows). |
| `query_sdmx` | Fetch observations and run one read-only SQL query server-side in a temporary in-memory table — returns only the result. Works on the hosted server; no row cap on the fetch. |
| `get_sdmx_vector_data` | Observations for a single vectorId via SDMX. |
| `get_sdmx_key_for_dimension` | All leaf member IDs for a dimension as a ready-to-paste OR key — excludes totals and subtotals, so sums and rankings don't double-count (e.g. NOC, CMAs). |

**Key syntax** (passed to `get_sdmx_data`):
- `"1.2.1"` — Geography=1, Gender=2, Age=1
- `".2.1"` — all geographies (wildcard), Gender=2, Age=1
- `"1+2.2.1"` — Geography 1 or 2, Gender=2, Age=1

> **Note:** Wildcard (`.`) returns every member of the dimension, including totals and parent aggregates. For sums or rankings use leaf codes from `get_sdmx_key_for_dimension`. Large wildcards can exceed `get_sdmx_data`'s 500-row cap; use `query_sdmx` for those.

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
| `get_changed_series_list` | Series updated today (available after 08:30 ET); for historical dates, use `get_changed_cube_list(date)`. |
| `get_changed_series_data_from_cube_pid_coord` | Data points that changed **today** for a coordinate (`changed: false` before 08:30 ET or if unchanged). |
| `get_changed_series_data_from_vector` | Data points that changed **today** for a vectorId (`changed: false` before 08:30 ET or if unchanged). |
| `get_bulk_vector_data_by_range` | Multiple vectors filtered by release date range. |

### Composite & Database Tools *(local/stdio mode only)*

These tools are not available on the hosted Render server — SQLite is per-process and not shared across users.

| Tool | Description |
|---|---|
| `fetch_sdmx_to_database` | Fetch SDMX observations (productId + key) into the observation store — no row cap, rows stay out of context. `table_name` becomes a view. |
| `fetch_vectors_to_database` | Fetch vectors by reference period range into the same store. `table_name` becomes a view. |
| `store_cube_metadata` | Fetch full cube metadata into SQLite — browse all members and vectorIds with SQL. |
| `query_database` | Read-only SQL against the local SQLite database. |
| `create_table_from_data` / `insert_data` | Create or append to a table of your own data. |
| `list_tables` / `get_table_schema` / `drop_table` | Database utilities (tables and views; `list_tables` also reports store size). |

**Observation store.** Both fetch tools upsert into two shared tables, so data accumulates instead of being copied into a new table per call:

| Table | One row per | Key columns |
|---|---|---|
| `_statcan_series` | series | `series_id` (`<productId>:<SDMX key>`, e.g. `18100004:2.2`), `product_id`, `vector_id`, `dims_json` (labels), `uom` |
| `_statcan_observations` | series × period | `series_id`, `ref_date` (period start), `period` (`2026`, `2026-Q2`, `2026-08`), `value`, `status`, `source`, `fetched_at`, `release_time` |

- Re-fetching updates values in place; each fetch reports how many observations were `new`, `revised` or `unchanged`.
- An SDMX and a WDS fetch of the same series share rows (WDS coordinates map to the same SDMX key).
- `table_name` is a view over the series and periods that call fetched, with the same columns as before (dimension labels, `period`, `value`, `VECTOR_ID`, `UOM`, ...).
- Cross-table analysis needs no schema discovery:

```sql
-- Seasonal component: CPI not seasonally adjusted (18100004) minus seasonally adjusted (18100006)
SELECT nsa.period, ROUND(nsa.value - sa.value, 2) AS seasonal
FROM _statcan_observations nsa JOIN _statcan_observations sa USING (ref_date)
WHERE nsa.series_id = '18100004:2.2' AND sa.series_id = '18100006:1.1'
ORDER BY ref_date DESC;
```

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
statcan download 14-10-0287-01 --key "1.1.1" --last 24 --output ./lfs.csv  # run `statcan metadata <pid>` first to find real dimension IDs
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
│   │   └── sdmx_tools.py        # get_sdmx_structure, get_sdmx_data, query_sdmx, get_sdmx_key_for_dimension
│   ├── composite_tools.py       # fetch_sdmx_to_database, fetch_vectors_to_database, store_cube_metadata (stdio only)
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
├── db/                          # SQLite: observation store (store.py), per-request SQL for query_sdmx (ephemeral.py), schema, queries
├── models/                      # Pydantic input models
├── util/
│   ├── registry.py              # ToolRegistry — @decorator → MCP Tool schema
│   ├── truncation.py            # Response truncation + pagination guidance
│   ├── sdmx_xml.py              # SDMX-ML (structure-specific XML) → labelled tabular rows
│   └── cache.py                 # 1-hour TTL cache for cube list
├── config.py                    # BASE_URL, SDMX_BASE_URL, RENDER_BASE_URL, TRANSPORT, PORT
└── server.py                    # create_server(), MCP Prompts, resources, HTTP transport, CLI
```

---

## Known Issues

| Issue | Status | Workaround |
|---|---|---|
| **"Unable to open database file" on Claude Desktop** | Active | Pass `--db-path /Users/<you>/.statcan-mcp/statcan_data.db` in your config |
| **SSL verification on broken trust stores** | Configurable | Verification is on by default; set `STATCAN_VERIFY_SSL=false` only if your system can't validate StatCan's certificate |
| **`lastNObservations` + `startPeriod`/`endPeriod` → 406** | Active | Use one or the other, not both |
| **Wildcard/OR rows missing or mislabelled; wrong `VECTOR_ID`/`UOM`** | Fixed in v0.12.0 | Caused by StatCan's SDMX-JSON index encoding; data is now read as structure-specific XML ([#90](https://github.com/Aryan-Jhaveri/mcp-statcan/issues/90)) |
| **Context overflow may cause data fabrication** | Mitigated | Use `query_sdmx` (hosted) or `fetch_sdmx_to_database` (local) so raw rows never enter context; `get_sdmx_data` caps inline rows at 500 |

---

## Contributors

Thanks to everyone who has contributed code, fixes and bug reports:

- [@Aryan-Jhaveri](https://github.com/Aryan-Jhaveri): creator and maintainer
- [@dannyward630](https://github.com/dannyward630): fixed `get_changed_series_list` to use StatCan's undated endpoint ([#130](https://github.com/Aryan-Jhaveri/mcp-statcan/pull/130))

Want to help? See [CONTRIBUTING.md](CONTRIBUTING.md).

---

<div align="center">Made with ❤️❤️❤️ for Statistics Canada</div>

<div align="center">
<a href="https://github.com/Aryan-Jhaveri/mcp-statcan" target="_blank">GitHub</a> •
<a href="https://github.com/Aryan-Jhaveri/mcp-statcan/issues" target="_blank">Report Bug</a> •
<a href="https://www.statcan.gc.ca/" target="_blank">Statistics Canada</a>
</div>

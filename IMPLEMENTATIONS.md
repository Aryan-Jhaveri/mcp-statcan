# Roadmap & Implementation Status
*Updated Feb 28, 2026*

---

## Up Next (Priority Order)

### 0 — Tool Cleanup (quick wins, before Phase 2)

**A. Consolidate coord tools**

`get_series_info_from_cube_pid_coord` (single) and `get_series_info_from_cube_pid_coord_bulk` (list) are redundant from the LLM's perspective. Merge into one tool that accepts either a single `(productId, coordinate)` pair or a list of them — same tool, same output format.

- [ ] Audit `cube_tools.py` for duplicate `get_series_info_from_cube_pid_coord` definition
- [ ] Merge single + bulk into one tool: `get_series_info` accepting `items: list[{productId, coordinate}]` with `limit`/`offset` for large batches
- [ ] Deregister old single/bulk tools (comment decorator), keep functions

**B. Any other redundant/confusing tools to audit?** *(check docstrings for LLM confusion risk)*

### Phase 2 — HTTP Transport *(next, after tool cleanup)*

#### Approach

Do **not** merge the stale `http` branch — it uses FastMCP which is unnecessary. The standard `mcp` SDK (>=1.3.0, already a dependency) supports Streamable HTTP transport. Build HTTP support directly on the existing `server.py` + `ToolRegistry` pattern.

**Stateless server architecture:**
- Server is a pure API proxy — fetches StatCan/SDMX data and returns it, stores nothing server-side
- DB tools excluded from HTTP mode (no per-user storage)
- Each client manages its own local SQLite via a separate `statcan-db-server` stdio sidecar (optional)
- SDMX tools are especially well-suited for HTTP mode — filtered responses, no storage needed
- Unlocks hosting on Render, Railway, Cloudflare Workers

**Implementation:**
- Add `--transport [stdio|http]` CLI flag to `server.py`
- In HTTP mode: skip `register_composite_tools` and `register_db_tools`
- Configure host/port via env vars or CLI args
- Auth: evaluate OAuth vs API key based on Python SDK support at implementation time

- [ ] Add `--transport` CLI flag; wire Streamable HTTP transport from `mcp` SDK
- [ ] Exclude DB/composite tools in HTTP mode
- [ ] Deploy to Render/Railway as a public free-tier instance
- [ ] Audit `fetch_vectors_to_database` and `store_cube_metadata` — provide pure-return variants for HTTP mode

---

### Phase 3 — MCP Resources & Prompts for SDMX *(after HTTP is stable)*

Expose SDMX URL construction as MCP primitives — supplementary to the SDMX tools, not a replacement.

- **Resource template:** `sdmx://statcan/data/{productId}/{key}` → resolves to the constructed SDMX URL and usage instructions
- **Prompt:** "SDMX data analysis" → reusable template with step-by-step URL construction guide, format notes, and `sdmx1`/`pandas` Python usage examples

These are additive — registered alongside tools in `create_server()`, no architectural change needed.

- [ ] Add `server.list_resources()` / `server.read_resource()` handlers
- [ ] Add `server.list_prompts()` / `server.get_prompt()` handlers
- [ ] SDMX URL construction prompt with Python usage examples

---

### Phase 4 — MCP Apps / Data Visualization *(post-HTTP, post-Python SDK support)*

Return interactive HTML charts/dashboards in-chat via `ui://` resources.

**No overhaul required.** MCP Apps are an additive primitive — registered alongside existing tools via a new handler, not a replacement for the existing architecture. The `ToolRegistry` pattern, all WDS tools, SDMX tools, and DB tools remain unchanged. Apps would be a new module (`src/api/app_tools.py`) registered in `create_server()` the same way as `register_cube_tools(registry)`.

**Architecture clarification — where visualization tools live:**

`visualize_table` queries *local* SQLite. This creates a hard split between the two server modes:

- **Local stdio server** — has SQLite. Visualization tools register here alongside DB tools. Works naturally.
- **Remote HTTP server** — stateless, no SQLite. Visualization tools are *excluded* from the HTTP build. Users who want charts use the local `statcan-db-server` stdio sidecar, where both DB tools and visualization tools live.

This is consistent with the existing DB split: remote HTTP server = API proxy only, local stdio sidecar = DB layer + everything that depends on it. Visualization is part of the DB layer, not the API layer.

**Current blockers:**
- Python MCP SDK does not yet support MCP Apps (JS SDK only, as of Feb 2026)
- Requires HTTP transport (stdio cannot serve HTML resources back to client)
- Limited host support — few MCP clients render `ui://` resources

**Unblocked when:** Phase 2 (HTTP transport) is live + Python SDK ships MCP Apps support.

---

## Context Window / Chat Memory — Design Principles

The core tension: tool results must be in context for the LLM to reason about them, but context is finite, expensive, and accumulates silently across a session. Large tool results don't disappear — they sit in conversation history and inflate the cost of every subsequent API call.

**Three-layer defense:**

1. **Precision fetching at source (SDMX)** — dimensional filtering in the URL means smaller responses before any truncation. `lastNObservations=12` limits to one year of monthly data. `/data/DF_18100004/1.2.7.0.0.0.0.0.0.0` fetches one series, not a whole table.

2. **Summary-first pattern (existing + SDMX)** — return stats/schema by default, full data only on explicit request. `get_sdmx_structure` returns the schema without any observations. `get_cube_metadata(summary=True)` caps member lists.

3. **URL passthrough** — every SDMX tool response includes `_sdmx_url`. Clients with execution environments (Claude Code, Claude.ai analysis sandbox) can fetch outside the MCP context entirely — data never enters conversation history. Claude Desktop users without a sandbox fall back to tool-mediated fetching with truncation.

**How Claude.ai handles overflow (observed):**
When a tool result exceeds context limits, Claude.ai stores it at `/mnt/user-data/tool_results/statcan_{tool}_{id}.json` and returns a path. The file format is `[{"text": "<json-string>"}]` — requiring double-parse. The LLM then uses Python scripts in the analysis sandbox to navigate the file. This works but costs ~6 extra tool calls and significant reasoning overhead. The `store_cube_metadata` → `query_database` pattern avoids this by keeping the data in SQLite from the start.

---

## Quality

- [ ] **Enable SSL verification** — `VERIFY_SSL = False` is a security risk
- [ ] **CI/CD linting** — ruff + mypy on push/PR
- [ ] **Expand tests** — mock StatCan API responses; per-tool coverage (currently only truncation is tested)
- [ ] **Consolidate HTTP client usage** — most tools create inline `httpx.AsyncClient` instead of using shared `api/client.py` helpers

---

## Distribution

- [ ] **Register on Smithery.ai** — one-click install button
- [ ] **Submit to directories** — `punkpeye/awesome-mcp-servers`, PulseMCP
- [ ] **Multi-client config snippets** — Cursor, VS Code Copilot, Windsurf in README
- [ ] **Windows setup guide** — needs testing on Windows VM first
- [ ] **Dockerfile** — for Docker MCP Catalog listing

---

## Future / Exploratory

- [ ] **A2A + MCP** — multi-agent system exploration
- [ ] **Scheduled reports** — periodic LLM calls for dataset summaries
- [ ] **Caching aligned to StatCan update schedule** — time-based invalidation at StatCan's 8:30 AM ET release cadence
- [ ] **Full cube pre-fetch** — download all cube metadata to local DB for fully offline browsing (low priority; current search + on-demand fetch is sufficient)

---

## Architecture & Data Flow

### Current (stdio / local)

```mermaid
flowchart TD
    A[Claude/MCP Client] -->|MCP Protocol - stdio| B[MCP Server]

    B --> C{Tool Type}
    C -->|WDS Cube/Vector| D[StatCan WDS API]
    C -->|SDMX - Phase 1| S[StatCan SDMX API]
    C -->|DB Tools| E[SQLite ~/.statcan-mcp/]

    D -->|fetch_vectors_to_database\nstore_cube_metadata| F[Composite: fetch + store]
    F --> E

    D -->|paginated tools| G[offset + limit response]
    G -->|preview + guidance| A

    S -->|filtered by key + date| T[flat tabular rows + _sdmx_url]
    T --> A

    E --> I[create_table_from_data\nquery_database\nlist_tables\nget_table_schema\ndrop_table]
    I -->|SQL Results| A

    style A fill:#210d70
    style B fill:#70190d
    style E fill:#700d49
    style F fill:#0d5c70
    style S fill:#0d6b3a
```

### Target (HTTP / stateless remote)

```mermaid
flowchart TD
    A[Claude/MCP Client] -->|MCP Protocol - Streamable HTTP| B[MCP Server - stateless]
    A -->|MCP Protocol - stdio| DB[statcan-db-server - local sidecar]
    A -->|direct fetch via _sdmx_url| S[StatCan SDMX API]

    B -->|WDS proxy only| D[StatCan WDS API]
    B -->|SDMX proxy| S
    D -->|data payload| A
    S -->|filtered SDMX-JSON| A

    A -->|store fetched data| DB
    DB --> E[SQLite - local machine]
    E -->|SQL Results| A

    style A fill:#210d70
    style B fill:#70190d
    style DB fill:#0d5c70
    style E fill:#700d49
    style S fill:#0d6b3a
```

---

## Completed


#### Phase 1 Progress

- [x] Add SDMX constants to `config.py` — `SDMX_BASE_URL`, `SDMX_JSON_ACCEPT`, `SDMX_XML_ACCEPT`, `MAX_SDMX_ROWS`
- [x] `src/util/sdmx_json.py` — `flatten_sdmx_json(data)` SDMX-JSON → tabular rows
- [x] `src/models/sdmx_models.py` — `SDMXStructureInput`, `SDMXDataInput`, `SDMXVectorInput`
- [x] `src/api/sdmx_tools.py` — `register_sdmx_tools(registry)` with 3 tools
- [x] Wire `register_sdmx_tools` into `server.py`
- [x] `get_sdmx_structure(productId)` — XML parse → JSON summary with codelist truncation
- [x] `get_sdmx_data(productId, key, startPeriod?, endPeriod?, lastNObservations?)` — JSON fetch + flatten
- [x] `get_sdmx_vector_data(vectorId, startPeriod?, endPeriod?, lastNObservations?)` — JSON fetch + flatten
- [x] Deregister `get_data_from_cube_pid_coord_and_latest_n_periods` (comment out `@registry.tool()` in `cube_tools.py`)
- [x] Deregister `get_data_from_vectors_and_latest_n_periods` (comment out `@registry.tool()` in `vector_tools.py`)
- [x] Deregister `get_data_from_vector_by_reference_period_range` (comment out `@registry.tool()` in `vector_tools.py`)
- [ ] `build_sdmx_url(...)` *(optional, deferred to Phase 3 Prompts)*


### Phase 1 Complete — SDMX Tools + Bug Fixes *(Feb 28, 2026)*

- [x] `SDMX_BASE_URL`, `SDMX_JSON_ACCEPT`, `SDMX_XML_ACCEPT`, `MAX_SDMX_ROWS` added to `config.py`
- [x] `src/util/sdmx_json.py` — `flatten_sdmx_json(data)`: SDMX-JSON → tabular rows. Handles series dims, obs dims, series/obs attrs. `_deref()` for safe index lookup. Obs-level attributes take priority on name collision.
- [x] `src/models/sdmx_models.py` — `SDMXStructureInput`, `SDMXDataInput`, `SDMXVectorInput`
- [x] `src/api/sdmx_tools.py` — 3 tools: `get_sdmx_structure`, `get_sdmx_data`, `get_sdmx_vector_data`
- [x] `server.py` — `register_sdmx_tools` wired in
- [x] 3 WDS data-fetch tools deregistered (decorator commented, functions kept)
- [x] **Bug 1**: Monthly period — duplicate ID detection → `start[:7]`; annual keeps bare year
- [x] **Bug 2**: `lastNObservations` + `startPeriod/endPeriod` → clear ValueError; docstrings updated
- [x] **Bug 3** (partial): Global obs_key overflow fixed via `obs_idx % n_period_vals`. Geography labels for OR-key series 2+ remain wrong (StatCan API bug) — wildcard recommended
- [x] Tests: `tests/test_sdmx_json.py` (7 tests); 22/22 passing

### Metadata Navigation Guidance — v0.2.1 *(Feb 26, 2026)*

**Problem observed:** An LLM session attempting to build a CPI + Labour Force dashboard hit a cascade of failures caused by metadata truncation and misleading guidance:

1. `summary=True` showed only 5 members per dimension — critical members like "Unemployment" (member 6) and "Unemployment rate" (member 7) were hidden. The LLM spent pages of reasoning guessing what coordinate positions meant.
2. `summary=False` produced 285KB of JSON — overflowed the context window. The client stored it to a file, forcing the LLM to install `jq` and write Python scripts to parse JSON-within-JSON (`data[0]['text']`).
3. The `_message` guidance said "get all members and their **vectorIds**" — but `getCubeMetadata` **does not return vectorIds** in member objects. VectorIds only come from `get_series_info_from_cube_pid_coord`. The LLM followed dead-end advice.
4. `_note` (top-level) and `_message` (per-dimension) were redundant, both saying "call with summary=False".
5. No guidance explained the coordinate-to-memberId mapping, so the LLM couldn't reason about which coordinate positions to use.

**Fixes applied:**
- [x] **`DEFAULT_MEMBER_LIMIT` 5 → 10** — shows more members before truncation
- [x] **Removed `_note`** — redundant with per-dimension `_message`
- [x] **Rewrote `_message` with actionable guidance** — explains coordinate position mapping, directs to `store_cube_metadata` and `get_series_info_from_cube_pid_coord`. Removed false vectorId claim.

**Key learning:** `getCubeMetadata` returns member names and hierarchy but **not vectorIds**. The three paths to vectorIds are:
1. `get_series_info_from_cube_pid_coord(productId, coordinate)` — resolve one coordinate at a time
2. `get_series_info_from_cube_pid_coord_bulk(items)` — resolve many coordinates in one call
3. `store_cube_metadata(productId)` → `query_database` — browse all members via SQL

### Context Window Overflow — v0.2.0 *(Feb 26, 2026)*
- [x] **`summarize_cube_metadata` default reduced 20 → 5** — `DEFAULT_MEMBER_LIMIT = 5` in `src/util/truncation.py`; 2 new tests added (15 total)
- [x] **Footnote stripping in summary mode** — replaces full `footnote` array with a count string
- [x] **`store_cube_metadata(pid)` composite tool** — fetches full metadata, stores into `_statcan_dimensions` + `_statcan_members`; returns compact summary only
- [x] **`get_cube_metadata` docstring updated** — points LLMs to `store_cube_metadata` for full member browsing without context cost

### Context Overflow & Truncation *(Feb 25, 2026)*
- [x] **Shared truncation utility** — `src/util/truncation.py`: `truncate_response`, `truncate_with_guidance`, `summarize_cube_metadata`; 13 unit tests
- [x] **`get_cube_metadata` summary mode** — `summary=True` (default) caps member lists; `summary=False` returns full response
- [x] **Cube list pagination** — `get_all_cubes_list` / `get_all_cubes_list_lite` paginated via `CubeListInput(offset, limit=100)`
- [x] **Search result cap** — `search_cubes_by_title` capped at `max_results=25`
- [x] **Bulk coord truncation + guidance** — `get_series_info_from_cube_pid_coord_bulk` paginates + injects `_guidance`
- [x] **Research: cursor-based pagination** — concluded it doesn't solve the problem; context overflow is caused by data accumulating in the window, not pagination inconsistency. Store-then-query is the correct direction.

### High-Priority Fixes *(Feb 25, 2026)*
- [x] **Bump `mcp>=1.3.0,<2`** — fixes protocol version mismatch; unlocks concurrent requests, Lifespan API, server `instructions` field
- [x] **Smart truncation for vector tools** — replaced auto-store with offset/limit pagination
- [x] **Bulk coord tool** — `get_series_info_from_cube_pid_coord_bulk` eliminates N sequential HTTP calls
- [x] **Registry `$defs` support** — `ToolRegistry` includes `$defs` in inputSchema for nested Pydantic models
- [x] **DB path fix** — `config.py` uses `pwd.getpwuid(os.getuid()).pw_dir`; `--db-path` CLI flag

### Core Data-Fetching Fixes *(Feb 25, 2026)*
- [x] `create_table_from_data` creates schema + inserts rows in one call
- [x] `fetch_vectors_to_database` composite tool — fetch + store in SQLite in a single call
- [x] Rewrote tool docstrings with workflow hints steering LLMs toward bulk vector pattern
- [x] Stable DB path at `~/.statcan-mcp/statcan_data.db`

### Distribution & Publishing *(Feb 23, 2026)*
- [x] PyPI — `pip install statcan-mcp-server` / `uvx statcan-mcp-server`; Trusted Publishing via GitHub OIDC
- [x] MCP Registry — `io.github.Aryan-Jhaveri/mcp-statcan`
- [x] GitHub Actions CI/CD — auto-publishes on push to `main`
- [x] Full StatCan WDS API coverage (~15 tools)
- [x] In-memory TTL cache for `search_cubes_by_title`
- [x] SQLite database layer — create, insert, query, list, schema, drop tools
- [x] `query_database` hardened — `PRAGMA query_only = ON` enforces read-only at SQLite engine level

---

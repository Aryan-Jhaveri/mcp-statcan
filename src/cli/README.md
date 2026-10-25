# statcan CLI

Standalone command-line interface for downloading Statistics Canada data — no LLM or MCP client required.

Installed alongside `statcan-mcp-server` as a separate entry point:

```bash
pip install statcan-mcp-server
statcan --help
```

Or run without installing:

```bash
uvx statcan-mcp-server
statcan --help
```

---

## Commands

| Command | Description |
|---|---|
| `statcan search <term>` | Search tables by keyword (AND logic) |
| `statcan metadata <product-id>` | Show table dimensions and member IDs |
| `statcan download <product-id>` | Download observations via SDMX → CSV |
| `statcan vector <vector-id>...` | Download one or more vector series |
| `statcan codeset` | Show code definitions (UOM, frequency, scalar, status) |
| `statcan describe` | Commands, options, exit codes and JSON envelopes as JSON (for agents) |

---

## Quick examples

```bash
# Find a table
statcan search "consumer price index"

# Inspect dimensions before downloading
statcan metadata 18-10-0004-01

# Download last 12 periods (--key is required; run `statcan metadata` first to see dimensions)
statcan download 18-10-0004-01 --key "1.1.1" --last 12 --output cpi.csv

# Download a specific slice
statcan download 18-10-0004-01 --key "1.1.1" --start 2020-01 --end 2024-12

# Preview the SDMX URL without fetching
statcan download 18-10-0004-01 --key "1.1.1" --last 5 --dry-run

# Download by vector ID
statcan vector v41690973 v41690974 --last 24 --output series.csv
```

---

## Output formats

Data commands accept `--format csv | json | ndjson | table` and `--output <file>`.  
Data goes to **stdout**; progress and errors go to **stderr** — safe to pipe.

```bash
statcan download 14-10-0287-01 --key "1.1.1" --last 1 --format csv \
  | awk -F',' 'NR>1 && $1=="Canada"' \
  | sort -t',' -k5 -rn \
  | head -10
```

---

## Machine-readable mode (agents and scripts)

Put `--json` before the subcommand, or set `STATCAN_OUTPUT=json`:

```bash
statcan --json download 18-10-0004-01 --key "2+3.2" --last 12 --output cpi.csv
```

```json
{"ok": true, "command": "download", "rows": 24, "columns": ["Geography", "..."],
 "product_id": 18100004, "key": "2+3.2", "source_url": "https://...",
 "period_range": ["2025-10", "2026-09"], "series_count": 2,
 "path": "cpi.csv", "format": "csv"}
```

Without `--output`, the envelope carries the rows in `data` instead of `path`.
Failures print one JSON object to **stderr**:

```json
{"ok": false, "error": {"code": "upstream_rejected", "exit_code": 4,
 "message": "StatCan rejected the query (HTTP 406)",
 "hint": "Run 'statcan metadata <product-id>' to see dimension positions..."}}
```

| Exit code | Name | Meaning |
|---|---|---|
| 0 | `ok` | Success |
| 1 | `error` | Unexpected error |
| 2 | `usage` | Invalid arguments or options |
| 3 | `not_found` | Product, vector or codeset not found |
| 4 | `upstream_rejected` | StatCan rejected the request (bad key or period); see `hint` |
| 5 | `upstream_unavailable` | Network error, timeout or StatCan 5xx; safe to retry |
| 6 | `empty` | Request succeeded but returned no rows |

`statcan describe` prints all of this plus every command's options as JSON.

---

## Source layout

```
src/cli/
├── main.py            # Typer app, --json root option, subcommand registration
├── contract.py        # exit codes, JSON envelopes, error → hint mapping
├── output.py          # write_output(), format helpers, normalize_product_id/vector_id
└── commands/
    ├── search.py      # statcan search
    ├── metadata.py    # statcan metadata
    ├── download.py    # statcan download
    ├── vector.py      # statcan vector
    ├── codeset.py     # statcan codeset
    └── describe.py    # statcan describe
```

The CLI calls the same SDMX/WDS HTTP logic as the MCP server (`src/api/`) — no duplicate business logic.

---

## For LLM agents (Claude Code)

Use the `/statcan-download` or `/statcan-data-lookup` MCP prompts to get ready-to-run command sequences. The typical pattern keeps data in `/tmp/` so it never enters the context window:

```bash
statcan --json search "topic"
statcan --json metadata <pid>
statcan --json download <pid> --key "1.1.1" --last 12 --output /tmp/data.csv
awk -F',' 'NR>1 && $1=="Canada"' /tmp/data.csv | sort -t',' -rn -k5 | head -10
```

Branch on the exit code rather than parsing messages: retry on 5, fix the key using `error.hint` on 4, widen the period on 6.

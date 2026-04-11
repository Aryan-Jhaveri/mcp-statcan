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

---

## Quick examples

```bash
# Find a table
statcan search "consumer price index"

# Inspect dimensions before downloading
statcan metadata 18-10-0004-01

# Download last 12 periods
statcan download 18-10-0004-01 --last 12 --output cpi.csv

# Download a specific slice
statcan download 18-10-0004-01 --key "1.1.1" --start 2020-01 --end 2024-12

# Preview the SDMX URL without fetching
statcan download 18-10-0004-01 --last 5 --dry-run

# Download by vector ID
statcan vector v41690973 v41690974 --last 24 --output series.csv
```

---

## Output formats

All commands accept `--format csv | json | table` and `--output <file>`.  
Data goes to **stdout**; progress and errors go to **stderr** — safe to pipe.

```bash
statcan download 14-10-0287-01 --last 1 --format csv \
  | awk -F',' 'NR>1 && $1=="Canada"' \
  | sort -t',' -k5 -rn \
  | head -10
```

---

## Source layout

```
src/cli/
├── main.py            # Typer app + subcommand registration
├── output.py          # write_output(), format helpers, normalize_product_id/vector_id
└── commands/
    ├── search.py      # statcan search
    ├── metadata.py    # statcan metadata
    ├── download.py    # statcan download
    ├── vector.py      # statcan vector
    └── codeset.py     # statcan codeset
```

The CLI calls the same SDMX/WDS HTTP logic as the MCP server (`src/api/`) — no duplicate business logic.

---

## For LLM agents (Claude Code)

Use the `/statcan-download` or `/statcan-data-lookup` MCP prompts to get ready-to-run command sequences. The typical pattern keeps data in `/tmp/` so it never enters the context window:

```bash
statcan search "topic"
statcan metadata <pid>
statcan download <pid> --last 12 --output /tmp/data.csv
awk -F',' 'NR>1 && $1=="Canada"' /tmp/data.csv | sort -t',' -rn -k5 | head -10
```

from mcp.types import Prompt, PromptArgument

from . import config
import re

_PROMPTS = {
    "statcan-data-lookup": Prompt(
        name="statcan-data-lookup",
        description=(
            "End-to-end workflow for finding and analyzing Statistics Canada data. "
            "Claude Code (bash): statcan CLI + awk pipelines. "
            "Claude.ai web: MCP tools for discovery, Python script fetches data to a local file — never floods context."
        ),
        arguments=[
            PromptArgument(
                name="topic",
                description="Data topic to search for (e.g. 'labour force', 'consumer price index')",
                required=False,
            ),
            PromptArgument(
                name="analysis_goal",
                description="What you want to learn from the data (e.g. 'trend over last 5 years', 'compare provinces')",
                required=False,
            ),
        ],
    ),
    "sdmx-key-builder": Prompt(
        name="sdmx-key-builder",
        description=(
            "Guide for building a precise SDMX key for get_sdmx_data or statcan download --key. "
            "Explains wildcard vs explicit member IDs, OR syntax, and dimension positions."
        ),
    ),
    "statcan-download": Prompt(
        name="statcan-download",
        description=(
            "Download a Statistics Canada table to CSV and analyze it. "
            "Claude Code (bash): statcan CLI + awk. "
            "Claude.ai web: Python script fetches to a local file — data never enters context."
        ),
        arguments=[
            PromptArgument(
                name="product_id",
                description="StatCan table productId (e.g. 14100287 or 14-10-0287-01)",
                required=True,
            ),
            PromptArgument(
                name="last_n",
                description="Number of most recent periods to download (default: 12)",
                required=False,
            ),
            PromptArgument(
                name="output_path",
                description="Output CSV path (default: ./statcan_<product_id>.csv)",
                required=False,
            ),
        ],
    ),
    "statcan-vector-pipeline": Prompt(
        name="statcan-vector-pipeline",
        description=(
            "Download one or more StatCan vector IDs to CSV and compare series with awk. "
            "Requires Claude Code (bash sandbox) with the statcan CLI installed."
        ),
        arguments=[
            PromptArgument(
                name="vector_ids",
                description="Space-separated vectorIds (e.g. 'v41690973 v41690974')",
                required=True,
            ),
            PromptArgument(
                name="output_path",
                description="Output CSV path (default: ./statcan_vectors.csv)",
                required=False,
            ),
        ],
    ),
    "statcan-explore": Prompt(
        name="statcan-explore",
        description=(
            "Sample and inspect a Statistics Canada table before committing to a full download. "
            "Claude Code (bash): statcan CLI. "
            "Claude.ai web: Python script samples to a local file — see column layout without flooding context."
        ),
        arguments=[
            PromptArgument(
                name="product_id",
                description="StatCan table productId to explore",
                required=True,
            ),
        ],
    ),
}


def get_prompt_text(name: str, args: dict) -> str:
    render_base = config.RENDER_BASE_URL or "https://mcp-statcan.onrender.com"

    if name == "statcan-data-lookup":
        topic = args.get("topic", "<your topic>")
        goal = args.get("analysis_goal", "<your analysis goal>")
        first_kw = topic if topic.startswith("<") else topic.split()[0]
        return (
            f"Statistics Canada data lookup\n"
            f"Topic: {topic}\n"
            f"Analysis goal: {goal}\n"
            "\n"
            "━━━ Claude Code (bash sandbox) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "\n"
            "Step 1 — Find the table:\n"
            f'  statcan search "{topic}" --max-results 10\n'
            "  → Note the Product ID of the best match.\n"
            "\n"
            "Step 2 — Explore structure before downloading:\n"
            "  statcan metadata <product-id>\n"
            "  statcan download <product-id> --last 3 --output ./sample.csv\n"
            "  head -2 ./sample.csv    # see column names and dimension positions\n"
            "\n"
            "Step 3 — Download data:\n"
            "  statcan download <product-id> --last 12 --output ./data.csv\n"
            "\n"
            "Step 4 — Analyze without loading the CSV into context:\n"
            "  head -2 ./data.csv                                     # column layout\n"
            "  awk -F',' 'NR>1 {{print $1}}' ./data.csv | sort -u       # unique dim values\n"
            "  awk -F',' 'NR>1 && $1==\"Canada\"' ./data.csv \\\n"
            "      | sort -t',' -rn -k N | head -10                      # top 10 by value\n"
            "  awk -F',' 'NR>1 && $1==\"Canada\" {{print $period_col, $value_col}}' \\\n"
            "      ./data.csv | sort                                   # time series\n"
            "\n"
            "Only the analysis output reaches the context window — not the raw CSV rows.\n"
            f"Adapt these patterns for: {goal}\n"
            "\n"
            "━━━ Claude.ai web (Python script) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "\n"
            "Use MCP tools for discovery only — fetch data via script so it lands\n"
            "in a local file, not the context window.\n"
            "\n"
            "Step 1 — Find the table:\n"
            f'  search_cubes_by_title(keywords=["{first_kw}"])\n'
            "  → Note the productId.\n"
            "\n"
            "Step 2 — Understand structure (small payload, no data):\n"
            "  get_sdmx_structure(productId=<id>)\n"
            "  → Read dimension positions and member codes. Build your key.\n"
            "  → For any dimension with >30 codes:\n"
            "  get_sdmx_key_for_dimension(productId=<id>, dimension_position=N)\n"
            "  → Paste the returned or_key at that dot-position.\n"
            "\n"
            "Step 3 — Fetch rows inline via MCP tool:\n"
            '  get_sdmx_rows(productId=<product-id>, key="<key>", lastNObservations=12)\n'
            "  → Returns rows directly in the tool response — no external fetch needed.\n"
            "  → Rows are capped at 500. Use a narrow key if you need fewer.\n"
            "\n"
            "Step 4 — Analyze the returned rows:\n"
            '  result = get_sdmx_rows(...)  # rows are in result["data"]\n'
            '  rows = result["data"]\n'
            "  cols = list(rows[0].keys()) if rows else []\n"
            '  top10 = sorted(rows, key=lambda r: float(r.get("value","0") or 0), reverse=True)[:10]\n'
            '  for r in top10: print(r.get("period"), r.get("value"))\n'
            f"  # Goal: {goal}\n"
            "\n"
            "WARNING: Never use wildcard (.) for dimensions with >30 codes — use or_key instead."
        )

    elif name == "sdmx-key-builder":
        return (
            "SDMX key construction guide for get_sdmx_data and statcan download --key:\n"
            "\n"
            "KEY FORMAT: dot-separated codes, one per dimension position (left to right).\n"
            '  "1.2.1"     = position-1 code 1, position-2 code 2, position-3 code 1\n'
            '  "1+2.2.1"   = position-1 code 1 OR 2, position-2 code 2, position-3 code 1\n'
            '  ".2.1"      = wildcard position-1 (all values), position-2 code 2, position-3 code 1\n'
            "\n"
            "WHICH CODES TO USE:\n"
            "  - Use member IDs from get_cube_metadata() or SDMX codelist code IDs\n"
            "  - WDS memberIds == SDMX codelist codes — same numbers, no translation needed\n"
            "  - Do NOT use the positional index of a code within get_sdmx_structure() output\n"
            "\n"
            "WILDCARD WARNING:\n"
            "  Wildcard (.) on a large dimension (>30 codes) returns only a sparse, unpredictable sample.\n"
            "  For NOC (309 codes), wildcard returned 31 rows; the correct full fetch needs 162 IDs.\n"
            "  Use get_sdmx_key_for_dimension(productId, dimension_position) to get the full OR key.\n"
            "\n"
            "OR KEY USAGE:\n"
            '  or_key from get_sdmx_key_for_dimension = "7+11+12+13+..." → paste at the right position:\n'
            '  key = f"7.3.1.1.1.{or_key}.1"\n'
            "\n"
            "TIME PARAMETERS (use only one, not both):\n"
            "  lastNObservations=N  → last N periods per series\n"
            '  startPeriod="YYYY"   → from year (or "YYYY-MM" for monthly)\n'
            '  endPeriod="YYYY-MM"  → up to this period\n'
            "  Combining lastNObservations + startPeriod/endPeriod → 406 error from StatCan.\n"
            "\n"
            "CLI USAGE (statcan download --key):\n"
            '  statcan download <product-id> --key "1.2.1+2.1" --last 12 --output ./data.csv\n'
            "  statcan download <product-id> --last 5 --dry-run   # preview SDMX URL before fetching\n"
            "\n"
            "INLINE ROWS VIA MCP TOOL (Claude.ai — use this instead of curl):\n"
            '  get_sdmx_rows(productId=<product-id>, key="<key>", lastNObservations=12)\n'
            '  get_sdmx_rows(productId=<product-id>, key="<key>", startPeriod="2020", endPeriod="2024")\n'
            "  → Returns rows directly — no external URL fetch needed.\n"
            '  → Rows are capped at 500. result["data"] is the list of dicts.\n'
            "\n"
            "CLI (curl / statcan CLI):\n"
            f"  {render_base}/files/sdmx/<product-id>/<key>?lastNObservations=12\n"
            f'  statcan download <product-id> --key "<key>" --last 12 --output ./data.csv'
        )

    elif name == "statcan-download":
        pid = args.get("product_id", "<product-id>")
        last_n = args.get("last_n", "12")
        _safe_pid = re.sub(r"[^a-zA-Z0-9\-]", "_", str(pid))
        out = args.get("output_path", f"./statcan_{_safe_pid}.csv")
        return (
            f"Download Statistics Canada table {pid}\n"
            "\n"
            "━━━ Claude Code (bash sandbox) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "\n"
            "# 1. Download data\n"
            f"statcan download {pid} --last {last_n} --output {out}\n"
            "\n"
            "# 2. Inspect column layout (note column numbers for filtering)\n"
            f"head -2 {out}\n"
            "\n"
            "# 3. Row count\n"
            f"awk 'NR>1' {out} | wc -l\n"
            "\n"
            "# 4. Unique values in first dimension (e.g. Geography)\n"
            f"awk -F',' 'NR>1 {{print $1}}' {out} | sort -u\n"
            "\n"
            "# 5. Unique values in second dimension (e.g. Sex, Industry)\n"
            f"awk -F',' 'NR>1 {{print $2}}' {out} | sort -u\n"
            "\n"
            "# 6. Filter to one dimension value\n"
            f"awk -F',' 'NR>1 && $1==\"Canada\"' {out}\n"
            "\n"
            "# 7. Top 10 by value (replace N with value column number from step 2)\n"
            f"awk -F',' 'NR>1' {out} | sort -t',' -rn -k N | head -10\n"
            "\n"
            "# 8. Time series for one geography (replace col numbers from step 2)\n"
            f"awk -F',' 'NR>1 && $1==\"Canada\" {{print $period_col, $value_col}}' {out} | sort -k1\n"
            "\n"
            "# 9. Latest period per vector (dedup by VECTOR_ID column)\n"
            f"sort -t',' -k period_col,period_col -r {out} | awk -F',' '!seen[$vector_col]++'\n"
            "\n"
            "# 10. Count non-empty values (exclude suppressed observations)\n"
            f"awk -F',' 'NR>1 && $value_col!=\"\"' {out} | wc -l\n"
            "\n"
            "Replace period_col, value_col, vector_col with actual column numbers from step 2.\n"
            "\n"
            "━━━ Claude.ai web (Python script) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "\n"
            "Step 1 — Get the table structure to build a key:\n"
            f"  get_sdmx_structure(productId={pid})\n"
            "  → For large dimensions (>30 codes):\n"
            f"  get_sdmx_key_for_dimension(productId={pid}, dimension_position=N)\n"
            "\n"
            "Step 2 — Fetch rows inline via MCP tool:\n"
            f'  get_sdmx_rows(productId={pid}, key="<key>", lastNObservations={last_n})\n'
            "  → Returns rows directly in the tool response — no external fetch needed.\n"
            '  → Rows are capped at 500. result["data"] is the list of dicts.\n'
            "\n"
            "Step 3 — Analyze the returned rows:\n"
            '  rows = result["data"]\n'
            "  cols = list(rows[0].keys()) if rows else []\n"
            '  print("Rows:", len(rows), "Cols:", cols)\n'
            '  top10 = sorted(rows, key=lambda r: float(r.get("value","0") or 0), reverse=True)[:10]\n'
            '  for r in top10: print(r.get("period"), r.get("value"))'
        )

    elif name == "statcan-vector-pipeline":
        vids = args.get("vector_ids", "<v41690973 v41690974>")
        out = args.get("output_path", "./statcan_vectors.csv")
        return (
            f"Multi-series vector pipeline: {vids}\n"
            "\n"
            "# 1. Download vectors\n"
            f"statcan vector {vids} --last 12 --output {out}\n"
            "\n"
            "# 2. Inspect column layout (VECTOR_ID and period columns are key)\n"
            f"head -2 {out}\n"
            "\n"
            "# 3. Unique vector IDs in the result\n"
            f"awk -F',' 'NR>1 {{print $vector_col}}' {out} | sort -u\n"
            "\n"
            "# 4. Row count per vector\n"
            f"awk -F',' 'NR>1 {{print $vector_col}}' {out} | sort | uniq -c | sort -rn\n"
            "\n"
            "# 5. Time series for each vector (period + value)\n"
            f"awk -F',' 'NR>1 {{print $vector_col, $period_col, $value_col}}' {out} | sort -k1,1 -k2,2\n"
            "\n"
            "# 6. Latest observation per vector\n"
            f"sort -t',' -k period_col,period_col -r {out} | awk -F',' '!seen[$vector_col]++'\n"
            "\n"
            "# 7. Cross-series at a specific period (replace YYYY with target year)\n"
            f"awk -F',' 'NR>1 && $period_col==\"YYYY\"' {out}\n"
            "\n"
            "# 8. Period-over-period change per vector\n"
            f"awk -F',' 'NR>1 {{print $vector_col, $period_col, $value_col}}' {out} \\\n"
            "    | sort -k1,1 -k2,2 \\\n"
            "    | awk '{{if (prev_vec==$1) print $1, $2, $3-prev_val; prev_vec=$1; prev_val=$3}}'\n"
            "\n"
            "Replace vector_col, period_col, value_col with actual column numbers from step 2."
        )

    elif name == "statcan-explore":
        pid = args.get("product_id", "<product-id>")
        _safe_pid = re.sub(r"[^a-zA-Z0-9\-]", "_", str(pid))
        sample_out = f"./explore_{_safe_pid}.csv"
        return (
            f"Explore Statistics Canada table {pid} before full download\n"
            "\n"
            "━━━ Claude Code (bash sandbox) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "\n"
            "# 1. Check table structure (dimensions, member counts)\n"
            f"statcan metadata {pid}\n"
            "\n"
            "# 2. Sample 3 most recent periods to see column layout\n"
            f"statcan download {pid} --last 3 --output {sample_out}\n"
            f"head -2 {sample_out}             # column names and positions\n"
            f"awk 'NR>1' {sample_out} | wc -l  # rows in 3-period sample\n"
            "\n"
            "# 3. Unique values in each dimension (adapt column numbers from step 2)\n"
            f"awk -F',' 'NR>1 {{print $1}}' {sample_out} | sort -u   # dim 1 (e.g. Geography)\n"
            f"awk -F',' 'NR>1 {{print $2}}' {sample_out} | sort -u   # dim 2 (e.g. Sex)\n"
            f"awk -F',' 'NR>1 {{print $3}}' {sample_out} | sort -u   # dim 3 (e.g. Industry)\n"
            "\n"
            "# 4. Estimate full dataset size\n"
            "#    rows_per_3_periods = result from step 2\n"
            "#    series_count = rows_per_3_periods / 3\n"
            "#    full_rows(last N) = series_count × N\n"
            "#    Use --key to narrow the query if size would be too large.\n"
            "\n"
            "# 5. Preview SDMX URL without downloading\n"
            f"statcan download {pid} --last 5 --dry-run\n"
            "\n"
            "# 6. Download with a focused key after exploring\n"
            f'statcan download {pid} --key "1.1.1" --last 24 --output ./data_{_safe_pid}.csv\n'
            "\n"
            "━━━ Claude.ai web (Python script) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "\n"
            "Step 1 — Check structure without fetching data (MCP tool):\n"
            f"  get_sdmx_structure(productId={pid})\n"
            "  → Count dimensions and codes. Note large dims (>30 codes).\n"
            "  → For large dims, call get_sdmx_key_for_dimension to get a narrow key first.\n"
            "\n"
            "Step 2 — Sample 3 periods to see column layout (MCP tool):\n"
            f'  get_sdmx_rows(productId={pid}, key="<narrow-key>", lastNObservations=3)\n'
            "  → key from Step 1 — avoid wildcards on large dims.\n"
            '  → Returns rows in result["data"].\n'
            '  rows = result["data"]\n'
            "  cols = list(rows[0].keys()) if rows else []\n"
            '  print("Columns:", cols)\n'
            '  print("Sample rows (3 periods):", len(rows))\n'
            '  print("Estimated series:", len(rows) // 3)\n'
            '  print("Projected rows for 12 periods: ~", (len(rows) // 3) * 12)\n'
            "\n"
            "Step 3 — Estimate size and decide.\n"
            "  If projected rows are too large, narrow the key further.\n"
            "  Then call get_sdmx_rows with lastNObservations=12 for the full fetch."
        )

    raise ValueError(f"Unknown prompt: {name}")

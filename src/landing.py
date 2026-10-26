"""Landing page served at / for the HTTP deployment."""

from importlib.metadata import version as _pkg_version, PackageNotFoundError as _PNF
try:
    _SERVER_VERSION = _pkg_version("statcan-mcp-server")
except _PNF:
    _SERVER_VERSION = "dev"

_HTML_TEMPLATE = """<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
  "http://www.w3.org/TR/html4/loose.dtd">
<html lang="en">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
<meta name="description" content="Statistics Canada MCP Server — Web Data Service Interface for Large Language Models">
<meta name="keywords" content="Statistics Canada, MCP, API, WDS, SDMX, data, Canada">
<title>Statistics Canada MCP Server :: Web Data Service Interface</title>
<link rel="icon" type="image/svg+xml" href="https://raw.githubusercontent.com/Aryan-Jhaveri/mcp-statcan/main/assets/logo.svg">
<link rel="icon" type="image/png" sizes="48x48" href="https://raw.githubusercontent.com/Aryan-Jhaveri/mcp-statcan/main/assets/logo-48.png">
<style type="text/css">
body {
  background-color: #FFFEF5;
  font-family: "Times New Roman", Times, serif;
  color: #000022;
  margin: 0;
  padding: 8px;
  font-size: 11pt;
}
a { color: #0000BB; text-decoration: underline; }
a:visited { color: #551A8B; }
a:hover { color: #CC0000; }
#wrapper {
  width: 800px;
  margin: 0 auto;
  border: 2px solid #003366;
  background: #FFFFFF;
}
#header {
  background: #003366;
  color: #FFFFFF;
  padding: 12px 16px 8px 16px;
  border-bottom: 3px solid #CC9900;
}
#header .logo {
  float: left;
  width: 56px;
  height: 56px;
  margin: 2px 12px 0 0;
}
#header h1 {
  margin: 0 0 2px 0;
  font-size: 22pt;
  font-weight: bold;
  letter-spacing: 1px;
}
#header .subtitle {
  font-size: 10pt;
  color: #CCDDEE;
  font-style: italic;
}
#header .byline {
  font-size: 9pt;
  color: #AABBCC;
  margin-top: 4px;
}
#nav {
  background: #E8EEF5;
  border-bottom: 1px solid #AAAAAA;
  padding: 4px 12px;
  font-size: 10pt;
  font-family: Arial, Helvetica, sans-serif;
}
#nav a { margin-right: 14px; font-weight: bold; color: #003366; }
#statusbar {
  background: #003366;
  color: #FFCC00;
  font-family: "Courier New", Courier, monospace;
  font-size: 8pt;
  padding: 2px 8px;
  text-align: right;
  letter-spacing: 0.5px;
}
#content { padding: 10px 16px; }
h2 {
  font-size: 14pt;
  color: #003366;
  border-bottom: 2px solid #003366;
  padding-bottom: 2px;
  margin-top: 18px;
}
h3 { font-size: 11pt; color: #660000; margin-bottom: 4px; }
.abstract {
  border: 1px dashed #999999;
  background: #FFFFF0;
  padding: 10px 14px;
  margin: 10px 0;
  font-style: italic;
  font-size: 10pt;
  line-height: 1.5;
}
.abstract strong { font-style: normal; }
.news-box {
  border: 2px inset #CCCCCC;
  background: #FFF8E8;
  padding: 6px 10px;
  font-size: 9.5pt;
  margin-bottom: 10px;
}
.new-badge {
  background: #CC0000;
  color: #FFFFFF;
  font-size: 8pt;
  font-family: Arial, sans-serif;
  font-weight: bold;
  padding: 1px 4px;
  margin-right: 4px;
  border: 1px solid #880000;
}
.endpoint-box {
  background: #F4F4F8;
  border: 1px solid #AAAAAA;
  border-left: 5px solid #003366;
  padding: 8px 12px;
  font-family: "Courier New", Courier, monospace;
  font-size: 9.5pt;
  margin: 8px 0;
  line-height: 1.6;
}
.endpoint-box .label {
  font-family: Arial, sans-serif;
  font-size: 8.5pt;
  font-weight: bold;
  color: #555555;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
table.tools {
  border-collapse: collapse;
  width: 100%;
  font-size: 9.5pt;
  margin: 8px 0;
}
table.tools th {
  background: #003366;
  color: #FFFFFF;
  border: 1px solid #001133;
  padding: 4px 8px;
  font-family: Arial, Helvetica, sans-serif;
  font-size: 9pt;
  text-align: left;
}
table.tools td {
  border: 1px solid #BBBBBB;
  padding: 3px 8px;
  vertical-align: top;
}
table.tools tr.even td { background: #EEF0F8; }
table.tools td.tool-name {
  font-family: "Courier New", Courier, monospace;
  font-size: 9pt;
  color: #003300;
  white-space: nowrap;
}
table.tools td.category {
  font-size: 8.5pt;
  font-style: italic;
  color: #444444;
  white-space: nowrap;
}
.specs-table {
  border-collapse: collapse;
  font-size: 10pt;
  margin: 8px 0;
}
.specs-table td {
  padding: 3px 12px 3px 0;
  vertical-align: top;
}
.specs-table td:first-child {
  font-weight: bold;
  color: #003366;
  white-space: nowrap;
  width: 160px;
}
.badge-row { margin: 12px 0 6px 0; font-size: 9pt; }
.badge {
  display: inline-block;
  border: 2px outset #CCCCCC;
  background: #DDDDDD;
  padding: 2px 6px;
  font-family: "Courier New", Courier, monospace;
  font-size: 8.5pt;
  margin-right: 6px;
  color: #000000;
}
.badge.green { background: #CCEECC; border-color: #88AA88; color: #003300; }
.badge.blue  { background: #CCDDEF; border-color: #8899BB; color: #001133; }
.badge.gold  { background: #FFEEAA; border-color: #AAAA55; color: #443300; }
hr.section { border: none; border-top: 1px solid #CCCCCC; margin: 14px 0; }
.recording {
  margin: 8px 0 14px 0;
  border: 2px inset #CCCCCC;
  background: #F4F4F8;
  padding: 4px;
}
.recording img { display: block; width: 100%; height: auto; }
.recording .caption {
  font-size: 8.5pt;
  font-style: italic;
  color: #444444;
  padding: 4px 2px 0 2px;
}
#footer {
  background: #E8EEF5;
  border-top: 2px solid #AAAACC;
  text-align: center;
  font-size: 8.5pt;
  color: #555555;
  padding: 8px;
  font-family: Arial, Helvetica, sans-serif;
}
.counter-text {
  font-family: "Courier New", Courier, monospace;
  font-size: 8pt;
  color: #888888;
}
.warning {
  background: #FFFACC;
  border: 1px solid #DDCC00;
  padding: 5px 10px;
  font-size: 9.5pt;
  margin: 8px 0;
}
.copy-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.copy-row code, pre.copy-src {
  font-family: "Courier New", Courier, monospace;
  font-size: 9.5pt;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
}
.copy-block { position: relative; }
.copy-block .copy-btn {
  position: absolute;
  top: 6px;
  right: 6px;
}
.copy-btn {
  font-family: Arial, Helvetica, sans-serif;
  font-size: 8pt;
  font-weight: bold;
  color: #003366;
  background: #DDDDDD;
  border: 2px outset #CCCCCC;
  padding: 1px 8px;
  cursor: pointer;
  white-space: nowrap;
}
.copy-btn:active { border-style: inset; }
.copy-btn.copied { background: #CCEECC; border-color: #88AA88; color: #003300; }
</style>
</head>
<body>
<div id="wrapper">

  <!-- HEADER -->
  <div id="header">
    <img class="logo" src="https://raw.githubusercontent.com/Aryan-Jhaveri/mcp-statcan/main/assets/logo.svg" alt="Maple leaf flag logo">
    <h1>Statistics Canada MCP Server</h1>
    <div class="subtitle">Web Data Service &amp; SDMX REST Interface for Large Language Models</div>
    <div class="byline">
      io.github.Aryan-Jhaveri/mcp-statcan &nbsp;|&nbsp;
      Transport: Streamable HTTP (stateless) &nbsp;|&nbsp;
      MCP endpoint: <tt>/mcp</tt>
    </div>
    <div style="clear: both;"></div>
  </div>

  <!-- NAV -->
  <div id="nav">
    <a href="/">Home</a>
    <a href="/health">Status</a>
    <a href="https://github.com/Aryan-Jhaveri/mcp-statcan">GitHub</a>
    <a href="https://www150.statcan.gc.ca/n1/en/type/data">StatCan</a>
  </div>

  <!-- STATUS BAR -->
  <div id="statusbar">
    SERVER STATUS: ONLINE &nbsp;|&nbsp; VERSION %%VERSION%% &nbsp;|&nbsp; TOOLS: 18 REGISTERED
  </div>

  <!-- CONTENT -->
  <div id="content">

    <div class="badge-row">
      <span class="badge blue">MCP SDK</span>
      <span class="badge green">SDMX REST</span>
      <span class="badge green">WDS REST</span>
      <span class="badge gold">v%%VERSION%%</span>
      <span class="badge">Python 3.10+</span>
      <span class="badge">Stateless HTTP</span>
    </div>

    <div class="news-box">
      <strong>Announcements:</strong><br>
      <span class="new-badge">NEW</span> v0.14.0 &mdash; interactive charts (MCP Apps): SDMX results render as a chart and table in Claude and other Apps hosts; the model gets a summary while the rows go to the view<br>
      <span class="new-badge">NEW</span> v0.13.0 &mdash; local installs: fetched data accumulates in one observation store (upserts with new/revised counts, shared across SDMX and WDS, cross-table joins); more resilient to StatCan timeouts<br>
      &bull; v0.12.0 &mdash; data correctness: SDMX data now read as XML; wildcards return every series (previously a partial set), and <tt>VECTOR_ID</tt>, <tt>DGUID</tt> and <tt>UOM</tt> are correct per row<br>
      &bull; v0.11.0 &mdash; <tt>statcan</tt> CLI for agents: <tt>--json</tt> envelopes, stable exit codes with hints, <tt>statcan describe</tt>; fixes for single-period monthly dates and frequency labels<br>
      &bull; v0.10.0 &mdash; structured output: SDMX tools publish an <tt>outputSchema</tt> and return typed <tt>structuredContent</tt>; failures are flagged <tt>isError</tt>; responses are 25&ndash;40% smaller<br>
      &bull; v0.9.0 &mdash; <tt>query_sdmx</tt> on this server: fetch a table slice and run one read-only SQL query server-side; only the answer is returned, with no 500-row cap on the fetch<br>
      &bull; v0.8.0 &mdash; <tt>fetch_sdmx_to_database</tt> (local install): store a full SDMX slice in SQLite without passing rows through the model; values stored as numbers<br>
      &bull; v0.7.16 &mdash; <tt>statcan download</tt> now requires <tt>--key</tt>; StatCan SDMX no longer accepts the <tt>all</tt> shortcut<br>
      &bull; v0.7.15 &mdash; OAuth 2.1/PKCE support: Claude.ai web connector now routes tool calls correctly<br>
      &bull; v0.7.14 &mdash; fixed 307 redirect loop on <tt>POST /mcp</tt>; Claude.ai IPs now receive 200 OK<br>
      &bull; v0.7.9 &mdash; automated CI/CD: version bumps on push, landing announcement workflow<br>
      &bull; v0.7.8 &mdash; tool-level request logging and <tt>/.well-known/mcp.json</tt> discovery<br>
      &bull; Listed on the MCP server registry<br>
    </div>

    <div class="abstract">
      <strong>Abstract.</strong>
      This server exposes Statistics Canada&rsquo;s <em>Web Data Service</em> (WDS) and
      <em>SDMX REST API</em> as a suite of Model Context Protocol (MCP) tools.
      Language models connect via the <tt>/mcp</tt> endpoint and gain structured access to
      over 7,000 Canadian statistical tables &mdash; labour force, GDP, inflation, demographics,
      health, environment, and more. The server operates in a fully <em>stateless</em> mode:
      no session state is retained between requests, enabling horizontal scaling and simplified
      deployment on platforms such as Render.
    </div>

    <!-- QUICK CONNECT -->
    <h2>Connection Instructions</h2>
    <p>
      Add this server to your MCP client using the <strong>Streamable HTTP</strong> transport.
      No API key is required &mdash; Statistics Canada data is publicly available.
    </p>

    <div class="endpoint-box">
      <span class="label">MCP Endpoint</span><br>
      <div class="copy-row">
        <code id="copy-endpoint">https://mcp-statcan.com/mcp</code>
        <button type="button" class="copy-btn" data-copy="copy-endpoint">Copy</button>
      </div>
      <br>
      <span class="label">Health Check</span><br>
      <div class="copy-row">
        <code id="copy-health">https://mcp-statcan.com/health</code>
        <button type="button" class="copy-btn" data-copy="copy-health">Copy</button>
      </div>
    </div>

    <h3>Claude Desktop (<tt>claude_desktop_config.json</tt>)</h3>
    <div class="endpoint-box copy-block">
      <button type="button" class="copy-btn" data-copy="copy-desktop">Copy</button>
<pre class="copy-src" id="copy-desktop">{
  "mcpServers": {
    "statcan": {
      "type": "http",
      "url": "https://mcp-statcan.com/mcp"
    }
  }
}</pre>
    </div>

    <h3>Claude Code (<tt>.mcp.json</tt>)</h3>
    <div class="endpoint-box copy-block">
      <button type="button" class="copy-btn" data-copy="copy-code-json">Copy</button>
<pre class="copy-src" id="copy-code-json">{
  "mcpServers": {
    "statcan": {
      "type": "http",
      "url": "https://mcp-statcan.com/mcp"
    }
  }
}</pre>
    </div>

    <h3>Claude Code (command line)</h3>
    <div class="endpoint-box">
      <div class="copy-row">
        <code id="copy-code-cli">claude mcp add --transport http statcan https://mcp-statcan.com/mcp</code>
        <button type="button" class="copy-btn" data-copy="copy-code-cli">Copy</button>
      </div>
    </div>

    <h3>Local install (stdio, includes SQLite tools and the <tt>statcan</tt> CLI)</h3>
    <div class="endpoint-box">
      <div class="copy-row">
        <code id="copy-pip">pip install statcan-mcp-server</code>
        <button type="button" class="copy-btn" data-copy="copy-pip">Copy</button>
      </div>
    </div>

    <h3>CLI for agents with a shell (JSON output, stable exit codes)</h3>
    <div class="endpoint-box">
      <div class="copy-row">
        <code id="copy-cli-describe">statcan describe</code>
        <button type="button" class="copy-btn" data-copy="copy-cli-describe">Copy</button>
      </div>
      <br>
      <div class="copy-row">
        <code id="copy-cli-download">statcan --json download 18-10-0004-01 --key "2+3.2" --last 12 --output cpi.csv</code>
        <button type="button" class="copy-btn" data-copy="copy-cli-download">Copy</button>
      </div>
    </div>

    <div class="warning">
      <strong>Note:</strong> This server is deployed on Render&rsquo;s free tier.
      The first request after a period of inactivity may take 30&ndash;60&nbsp;seconds
      while the instance spins up. Subsequent requests are fast.
    </div>

    <!-- MCP APPS VIEW -->
    <h2>Interactive Charts (MCP Apps)</h2>
    <p>
      In hosts that support MCP Apps, <tt>get_sdmx_data</tt>, <tt>get_sdmx_vector_data</tt> and <tt>query_sdmx</tt>
      open an interactive chart and table in the conversation. The model receives a short summary; the full rows go
      to the view, so large results don&rsquo;t fill the model&rsquo;s context.
    </p>
    <div class="recording">
      <img src="https://raw.githubusercontent.com/Aryan-Jhaveri/mcp-statcan/main/assets/mcp-app-series-view.png"
           alt="Interactive MCP Apps view: Consumer Price Index line chart for five geographies with a hover tooltip, legend, Chart/Table tabs, Download CSV and Open source buttons"
           width="760" loading="lazy">
      <div class="caption">CPI for five geographies: crosshair tooltip, legend, table view, CSV download</div>
    </div>

    <!-- CLI RECORDINGS -->
    <h2>Command-Line Interface</h2>
    <p>
      The <tt>statcan</tt> CLI ships with the local install and works without an LLM. People can
      browse tables in the terminal; agents with a shell can use <tt>--json</tt> for structured output
      and stable exit codes.
    </p>

    <h3>Exploring a table: search, metadata, download</h3>
    <div class="recording">
      <img src="https://raw.githubusercontent.com/Aryan-Jhaveri/mcp-statcan/main/assets/cli-explore.gif"
           alt="Terminal recording: statcan search, statcan metadata and statcan download for the Consumer Price Index table"
           width="760" loading="lazy">
      <div class="caption">statcan search &rarr; statcan metadata &rarr; statcan download (table output)</div>
    </div>

    <h3>Agent mode: JSON envelopes and exit codes</h3>
    <div class="recording">
      <img src="https://raw.githubusercontent.com/Aryan-Jhaveri/mcp-statcan/main/assets/cli-agent.gif"
           alt="Terminal recording: statcan --json download writes a CSV and prints a summary envelope; a missing product returns a JSON error with exit code 3; statcan describe lists exit codes"
           width="760" loading="lazy">
      <div class="caption">--json download writes the file and prints a summary; failures return a typed exit code and a hint</div>
    </div>

    <!-- TOOL INVENTORY -->
    <h2>Registered Tools (18)</h2>
    <p>
      All tools below are exposed over the <tt>/mcp</tt> endpoint. The hosted HTTP server
      runs in <em>stateless</em> mode &mdash; composite and SQLite database tools are intentionally
      omitted here. To use those, run the server locally over stdio
      (<tt>pip install statcan-mcp-server</tt>). For calculations on this server, use
      <tt>query_sdmx</tt>: the SQL runs here and only the answer is sent back to the model.
    </p>

    <table class="tools">
      <tr>
        <th>Tool Name</th>
        <th>Category</th>
        <th>Description</th>
      </tr>
      <tr class="odd"><td class="tool-name">search_cubes_by_title</td><td class="category">Discovery</td><td>Full-text keyword search across all StatCan tables, capped at 25 results</td></tr>
      <tr class="even"><td class="tool-name">get_all_cubes_list</td><td class="category">Discovery</td><td>Paginated inventory of all tables (100/page)</td></tr>
      <tr class="odd"><td class="tool-name">get_all_cubes_list_lite</td><td class="category">Discovery</td><td>Lightweight paginated list, 1-hour TTL cache</td></tr>
      <tr class="even"><td class="tool-name">get_cube_metadata</td><td class="category">Metadata</td><td>Full table structure: dimensions, members, frequencies; summary mode caps members at 10</td></tr>
      <tr class="odd"><td class="tool-name">get_code_sets</td><td class="category">Metadata</td><td>WDS attribute decoder tables (scalar type, UOM, frequency, status codes)</td></tr>
      <tr class="even"><td class="tool-name">get_series_info</td><td class="category">Series</td><td>Resolve dimension coordinates to vectorId, frequency, UOM</td></tr>
      <tr class="odd"><td class="tool-name">get_series_info_from_vector</td><td class="category">Series</td><td>Look up series metadata by vectorId</td></tr>
      <tr class="even"><td class="tool-name">get_bulk_vector_data_by_range</td><td class="category">Vector</td><td>Fetch multiple vectors filtered by release-date range</td></tr>
      <tr class="odd"><td class="tool-name">get_changed_series_data_from_vector</td><td class="category">Change Detection</td><td>Detect data changes for a vector since a given date</td></tr>
      <tr class="even"><td class="tool-name">get_changed_series_data_from_cube_pid_coord</td><td class="category">Change Detection</td><td>Detect changes for a specific series by coordinate</td></tr>
      <tr class="odd"><td class="tool-name">get_changed_cube_list</td><td class="category">Change Detection</td><td>List all tables with data changes since a given date</td></tr>
      <tr class="even"><td class="tool-name">get_changed_series_list</td><td class="category">Change Detection</td><td>List all series with changes since a given date</td></tr>
      <tr class="odd"><td class="tool-name">get_sdmx_structure</td><td class="category">SDMX</td><td>Data Structure Definition as JSON: dimension positions and codelists with hierarchy</td></tr>
      <tr class="even"><td class="tool-name">get_sdmx_data</td><td class="category">SDMX</td><td>Server-side filtered observations by productId + SDMX key string</td></tr>
      <tr class="odd"><td class="tool-name">get_sdmx_rows</td><td class="category">SDMX</td><td>Inline tabular rows (up to 500) returned directly in the tool response</td></tr>
      <tr class="even"><td class="tool-name">query_sdmx</td><td class="category">SDMX + SQL</td><td>Fetch observations and run one read-only SQL query server-side in a temporary in-memory table; returns only the result (rank, compare, growth)</td></tr>
      <tr class="odd"><td class="tool-name">get_sdmx_vector_data</td><td class="category">SDMX</td><td>Single vectorId observations via SDMX</td></tr>
      <tr class="even"><td class="tool-name">get_sdmx_key_for_dimension</td><td class="category">SDMX</td><td>Returns the full OR-key for a large dimension (avoids wildcard sampling errors)</td></tr>
    </table>

    <hr class="section">

    <!-- TECHNICAL SPECIFICATIONS -->
    <h2>Technical Specifications</h2>
    <table class="specs-table">
      <tr><td>Transport</td><td>Streamable HTTP (stateless) &mdash; MCP 2025-03-26 spec</td></tr>
      <tr><td>Upstream APIs</td><td>Statistics Canada WDS REST + SDMX 2.1 REST (data read as structure-specific XML)</td></tr>
      <tr><td>Authentication</td><td>OAuth 2.1/PKCE available (auto-approved, no credentials); open access also supported</td></tr>
      <tr><td>SSL Verification</td><td>On by default; <tt>STATCAN_VERIFY_SSL=false</tt> disables it for broken trust stores</td></tr>
      <tr><td>Structured Output</td><td><tt>outputSchema</tt> + <tt>structuredContent</tt> on all SDMX tools; read-only tools carry <tt>readOnlyHint</tt></td></tr>
      <tr><td>Max SDMX Rows</td><td>500 per <tt>get_sdmx_data</tt> call</td></tr>
      <tr><td>Server-side SQL</td><td><tt>query_sdmx</tt>: SQLite in-memory, one SELECT per call, 2&nbsp;s limit, up to 50,000 fetched rows, 500 result rows; nothing stored</td></tr>
      <tr><td>Cache</td><td>1-hour TTL on <tt>get_all_cubes_list_lite</tt></td></tr>
      <tr><td>Python</td><td>3.10+ &mdash; asyncio, httpx, Starlette, Uvicorn</td></tr>
      <tr><td>Install</td><td><tt>pip install statcan-mcp-server</tt></td></tr>
      <tr><td>Source</td><td><a href="https://github.com/Aryan-Jhaveri/mcp-statcan">github.com/Aryan-Jhaveri/mcp-statcan</a></td></tr>
    </table>

    <hr class="section">

    <!-- KNOWN CONSTRAINTS -->
    <h2>Known Constraints &amp; Notes</h2>
    <ul style="font-size:10pt; line-height:1.7;">
      <li><strong>lastNObservations + startPeriod/endPeriod</strong> &mdash; cannot be combined; StatCan returns HTTP&nbsp;406.</li>
      <li><strong>Wildcards include totals</strong> &mdash; <tt>.</tt> returns every member of a dimension, including totals and
          parent aggregates. For sums or rankings use leaf codes from <tt>get_sdmx_key_for_dimension</tt>.</li>
      <li><strong>vectorIds from metadata</strong> &mdash; <tt>get_cube_metadata</tt> returns member names but <em>not</em> vectorIds.
          Use <tt>get_series_info</tt> to resolve coordinates to vectorIds.</li>
      <li><strong>Data format</strong> &mdash; SDMX data is read as structure-specific XML and labelled from the table&rsquo;s
          structure. StatCan&rsquo;s SDMX-JSON mis-indexes series and attributes, which previously caused missing wildcard rows,
          wrong OR-key labels and misplaced <tt>VECTOR_ID</tt>/<tt>UOM</tt> values (fixed in v0.12.0).</li>
    </ul>

    <hr class="section">

    <!-- ATTRIBUTION -->
    <h2>Data Attribution</h2>
    <p style="font-size:10pt; line-height:1.6;">
      All data returned by this server originates from
      <a href="https://www150.statcan.gc.ca/n1/en/type/data">Statistics Canada</a>.
      Users are responsible for complying with Statistics Canada&rsquo;s
      <a href="https://www.statcan.gc.ca/en/reference/licence">Open Licence</a>
      when using or redistributing data obtained through this server.
      This MCP server is an independent project and is not affiliated with
      or endorsed by Statistics Canada or the Government of Canada.
    </p>

  </div><!-- /content -->

  <!-- FOOTER -->
  <div id="footer">
    <strong>Statistics Canada MCP Server</strong> &mdash; v%%VERSION%%<br>
    &copy; 2025 Aryan Jhaveri &nbsp;|&nbsp;
    <a href="https://github.com/Aryan-Jhaveri/mcp-statcan/blob/main/LICENSE">MIT Licence</a>
    &nbsp;|&nbsp;
    <a href="https://github.com/Aryan-Jhaveri/mcp-statcan/issues">Report an Issue</a><br>
    <span class="counter-text">
      Best viewed at 1024&times;768 &mdash; Optimized for MCP-compatible LLM clients
    </span>
  </div>

</div><!-- /wrapper -->
<script type="text/javascript">
(function () {
  function fallbackCopy(text) {
    var area = document.createElement("textarea");
    area.value = text;
    area.setAttribute("readonly", "");
    area.style.position = "absolute";
    area.style.left = "-9999px";
    document.body.appendChild(area);
    area.select();
    var ok = false;
    try { ok = document.execCommand("copy"); } catch (e) { ok = false; }
    document.body.removeChild(area);
    return ok;
  }
  function flash(btn, label) {
    btn.textContent = label;
    btn.className = label === "Copied" ? "copy-btn copied" : "copy-btn";
    setTimeout(function () { btn.textContent = "Copy"; btn.className = "copy-btn"; }, 1500);
  }
  var buttons = document.querySelectorAll(".copy-btn[data-copy]");
  for (var i = 0; i < buttons.length; i++) {
    buttons[i].addEventListener("click", function () {
      var btn = this;
      var src = document.getElementById(btn.getAttribute("data-copy"));
      if (!src) { return; }
      var text = src.textContent;
      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(
          function () { flash(btn, "Copied"); },
          function () { flash(btn, fallbackCopy(text) ? "Copied" : "Press Ctrl+C"); }
        );
      } else {
        flash(btn, fallbackCopy(text) ? "Copied" : "Press Ctrl+C");
      }
    });
  }
})();
</script>
</body>
</html>"""

_HTML = _HTML_TEMPLATE.replace("%%VERSION%%", _SERVER_VERSION)


async def landing_page(request) -> object:
    from starlette.responses import HTMLResponse
    return HTMLResponse(content=_HTML)

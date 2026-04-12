"""Landing page served at / for the HTTP deployment."""

_HTML = """<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
  "http://www.w3.org/TR/html4/loose.dtd">
<html lang="en">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
<meta name="description" content="Statistics Canada MCP Server — Web Data Service Interface for Large Language Models">
<meta name="keywords" content="Statistics Canada, MCP, API, WDS, SDMX, data, Canada">
<title>Statistics Canada MCP Server :: Web Data Service Interface</title>
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
</style>
</head>
<body>
<div id="wrapper">

  <!-- HEADER -->
  <div id="header">
    <h1>Statistics Canada MCP Server</h1>
    <div class="subtitle">Web Data Service &amp; SDMX REST Interface for Large Language Models</div>
    <div class="byline">
      io.github.Aryan-Jhaveri/mcp-statcan &nbsp;|&nbsp;
      Transport: Streamable HTTP (stateless) &nbsp;|&nbsp;
      MCP endpoint: <tt>/mcp</tt>
    </div>
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
    SERVER STATUS: ONLINE &nbsp;|&nbsp; VERSION 0.7.5 &nbsp;|&nbsp; TOOLS: 18 REGISTERED
  </div>

  <!-- CONTENT -->
  <div id="content">

    <div class="badge-row">
      <span class="badge blue">MCP SDK</span>
      <span class="badge green">SDMX REST</span>
      <span class="badge green">WDS REST</span>
      <span class="badge gold">v0.7.5</span>
      <span class="badge">Python 3.11+</span>
      <span class="badge">Stateless HTTP</span>
    </div>

    <div class="news-box">
      <strong>Announcements:</strong><br>
      <span class="new-badge">NEW</span> v0.7.5 &mdash; SDMX <tt>get_sdmx_rows</tt> for inline row fetching without context flood<br>
      <span class="new-badge">NEW</span> <tt>statcan</tt> CLI (Track 1) &mdash; download tables without an LLM client<br>
      &bull; Listed on the
      <a href="https://github.com/modelcontextprotocol/servers">MCP server registry</a>
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
      https://mcp-statcan.onrender.com/mcp<br><br>
      <span class="label">Health Check</span><br>
      https://mcp-statcan.onrender.com/health<br><br>
      <span class="label">SDMX CSV Proxy</span><br>
      https://mcp-statcan.onrender.com/files/sdmx/{product_id}/{key}?lastNObservations=12
    </div>

    <h3>Claude Desktop (<tt>claude_desktop_config.json</tt>)</h3>
    <div class="endpoint-box">
{<br>
&nbsp;&nbsp;"mcpServers": {<br>
&nbsp;&nbsp;&nbsp;&nbsp;"statcan": {<br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"type": "http",<br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"url": "https://mcp-statcan.onrender.com/mcp"<br>
&nbsp;&nbsp;&nbsp;&nbsp;}<br>
&nbsp;&nbsp;}<br>
}
    </div>

    <h3>Claude Code (<tt>.mcp.json</tt>)</h3>
    <div class="endpoint-box">
{<br>
&nbsp;&nbsp;"mcpServers": {<br>
&nbsp;&nbsp;&nbsp;&nbsp;"statcan": {<br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"type": "http",<br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"url": "https://mcp-statcan.onrender.com/mcp"<br>
&nbsp;&nbsp;&nbsp;&nbsp;}<br>
&nbsp;&nbsp;}<br>
}
    </div>

    <div class="warning">
      <strong>Note:</strong> This server is deployed on Render&rsquo;s free tier.
      The first request after a period of inactivity may take 30&ndash;60&nbsp;seconds
      while the instance spins up. Subsequent requests are fast.
    </div>

    <!-- TOOL INVENTORY -->
    <h2>Registered Tools (18)</h2>
    <p>All tools are available over the <tt>/mcp</tt> endpoint.</p>

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
      <tr class="even"><td class="tool-name">get_sdmx_vector_data</td><td class="category">SDMX</td><td>Single vectorId observations via SDMX</td></tr>
      <tr class="odd"><td class="tool-name">get_sdmx_key_for_dimension</td><td class="category">SDMX</td><td>Returns the full OR-key for a large dimension (avoids wildcard sampling errors)</td></tr>
      <tr class="even"><td class="tool-name">get_sdmx_key_for_dimension</td><td class="category">SDMX</td><td>Returns full codelist OR key for a single dimension position</td></tr>
    </table>

    <hr class="section">

    <!-- TECHNICAL SPECIFICATIONS -->
    <h2>Technical Specifications</h2>
    <table class="specs-table">
      <tr><td>Transport</td><td>Streamable HTTP (stateless) &mdash; MCP 2025-03-26 spec</td></tr>
      <tr><td>Upstream APIs</td><td>Statistics Canada WDS REST + SDMX 2.1 REST</td></tr>
      <tr><td>Authentication</td><td>None required (public data)</td></tr>
      <tr><td>SSL Verification</td><td>Disabled (<tt>VERIFY_SSL=False</tt>) &mdash; StatCan certificate quirk</td></tr>
      <tr><td>Max SDMX Rows</td><td>500 per <tt>get_sdmx_data</tt> call</td></tr>
      <tr><td>Cache</td><td>1-hour TTL on <tt>get_all_cubes_list_lite</tt></td></tr>
      <tr><td>Python</td><td>3.11+ &mdash; asyncio, httpx, Starlette, Uvicorn</td></tr>
      <tr><td>Install</td><td><tt>pip install mcp-statcan</tt></td></tr>
      <tr><td>Source</td><td><a href="https://github.com/Aryan-Jhaveri/mcp-statcan">github.com/Aryan-Jhaveri/mcp-statcan</a></td></tr>
    </table>

    <hr class="section">

    <!-- KNOWN CONSTRAINTS -->
    <h2>Known Constraints &amp; Notes</h2>
    <ul style="font-size:10pt; line-height:1.7;">
      <li><strong>lastNObservations + startPeriod/endPeriod</strong> &mdash; cannot be combined; StatCan returns HTTP&nbsp;406.</li>
      <li><strong>SDMX wildcard on large dimensions</strong> &mdash; <tt>.</tt> on dimensions with &gt;30 codes returns sparse,
          unpredictable samples. Use <tt>get_sdmx_key_for_dimension</tt> for the full OR key instead.</li>
      <li><strong>vectorIds from metadata</strong> &mdash; <tt>get_cube_metadata</tt> returns member names but <em>not</em> vectorIds.
          Use <tt>get_series_info</tt> to resolve coordinates to vectorIds.</li>
      <li><strong>Geography OR key</strong> &mdash; known StatCan encoding bug for Geography dimension labels in OR-key syntax;
          use wildcard for Geography.</li>
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
    <strong>Statistics Canada MCP Server</strong> &mdash; v0.7.5<br>
    &copy; 2025 Aryan Jhaveri &nbsp;|&nbsp;
    <a href="https://github.com/Aryan-Jhaveri/mcp-statcan/blob/main/LICENSE">MIT Licence</a>
    &nbsp;|&nbsp;
    <a href="https://github.com/Aryan-Jhaveri/mcp-statcan/issues">Report an Issue</a><br>
    <span class="counter-text">
      Best viewed at 1024&times;768 &mdash; Optimized for MCP-compatible LLM clients
    </span>
  </div>

</div><!-- /wrapper -->
</body>
</html>"""


async def landing_page(request) -> object:
    from starlette.responses import HTMLResponse
    return HTMLResponse(content=_HTML)

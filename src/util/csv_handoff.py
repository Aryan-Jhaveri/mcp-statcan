"""Experimental CSV handoff (#169): send a format="csv" result as an MCP resource.

Question being tested: does a client such as claude.ai put a tool result's
resource into its code sandbox as a file, so the agent doesn't retype the rows?

STATCAN_CSV_HANDOFF selects how a get_sdmx_data(format="csv") result is sent:
  off (default)  metadata JSON block + raw CSV text block (#168), unchanged
  embedded       metadata JSON block + EmbeddedResource (text/csv); no raw CSV text,
                 so whatever the model sees of the CSV came through the resource
  embedded+text  both: the resource and the raw CSV text block
  link           metadata JSON block + ResourceLink; the server reads the URI back
                 via resources/read by re-running the query (stateless, nothing stored)

URIs encode the query: statcan://csv/<productId>/<key>?<params> or
statcan://csv/v<vectorId>?<params>, where params are lastNObservations,
startPeriod, endPeriod and sql.
"""

import os
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlsplit

from mcp.types import (
    EmbeddedResource,
    ListResourcesResult,
    ListResourceTemplatesResult,
    ReadResourceResult,
    ResourceLink,
    ResourceTemplate,
    TextContent,
    TextResourceContents,
)

MODES = ("off", "embedded", "embedded+text", "link")
MIME = "text/csv"
SCHEME = "statcan://csv/"
_QUERY_PARAMS = ("lastNObservations", "startPeriod", "endPeriod", "sql")


def handoff_mode() -> str:
    mode = (os.environ.get("STATCAN_CSV_HANDOFF") or "off").strip().lower()
    if mode not in MODES:
        raise ValueError(f"Unknown STATCAN_CSV_HANDOFF {mode!r}; use one of: {', '.join(MODES)}.")
    return mode


def csv_uri(arguments: Dict[str, Any]) -> str:
    """The query behind a get_sdmx_data call, as a statcan://csv/ URI."""
    if arguments.get("vectorId") is not None:
        path = f"v{int(arguments['vectorId'])}"
    else:
        path = f"{int(arguments['productId'])}/{quote(str(arguments.get('key', '')), safe='.+')}"
    params = {k: arguments[k] for k in _QUERY_PARAMS if arguments.get(k) is not None}
    return SCHEME + path + (f"?{urlencode(params)}" if params else "")


def parse_csv_uri(uri: str) -> Dict[str, Any]:
    """statcan://csv/ URI → get_sdmx_data arguments (format="csv")."""
    if not uri.startswith(SCHEME):
        raise ValueError(f"Unknown resource URI: {uri}")
    parts = urlsplit(uri)
    path = uri[len(SCHEME):].split("?", 1)[0]
    args: Dict[str, Any] = {"format": "csv"}
    if path.startswith("v"):
        args["vectorId"] = int(path[1:])
    else:
        product, _, key = path.partition("/")
        args["productId"] = int(product)
        args["key"] = unquote(key)
    for k, v in parse_qsl(parts.query, keep_blank_values=True):
        if k in _QUERY_PARAMS:
            args[k] = int(v) if k == "lastNObservations" else v
    return args


def _name(arguments: Dict[str, Any]) -> str:
    if arguments.get("vectorId") is not None:
        return f"statcan_v{arguments['vectorId']}.csv"
    return f"statcan_{arguments.get('productId')}.csv"


def content_blocks(meta_text: str, csv_text: str, arguments: Dict[str, Any], mode: str) -> List[Any]:
    """Content for a format="csv" result in a handoff mode other than off."""
    uri = csv_uri(arguments)
    meta = TextContent(type="text", text=meta_text)
    if mode == "link":
        link = ResourceLink(
            type="resource_link", uri=uri, name=_name(arguments), mime_type=MIME,
            description="The CSV for this query; read it with resources/read.",
            size=len(csv_text.encode("utf-8")),
        )
        return [meta, link]
    resource = EmbeddedResource(
        type="resource", resource=TextResourceContents(uri=uri, mime_type=MIME, text=csv_text)
    )
    if mode == "embedded+text":
        return [meta, resource, TextContent(type="text", text=csv_text)]
    return [meta, resource]


def resource_handlers(registry) -> Dict[str, Any]:
    """Server handlers that make statcan://csv/ URIs readable (link mode)."""

    async def on_list_resources(ctx, params) -> ListResourcesResult:
        return ListResourcesResult(resources=[])  # URIs come from tool results

    async def on_list_resource_templates(ctx, params) -> ListResourceTemplatesResult:
        return ListResourceTemplatesResult(resource_templates=[
            ResourceTemplate(
                name="sdmx_csv", uri_template=SCHEME + "{productId}/{key}{?lastNObservations,startPeriod,endPeriod,sql}",
                mime_type=MIME, description="get_sdmx_data(format='csv') for a table and key.",
            ),
            ResourceTemplate(
                name="vector_csv", uri_template=SCHEME + "v{vectorId}{?lastNObservations,startPeriod,endPeriod,sql}",
                mime_type=MIME, description="get_sdmx_data(format='csv') for one vector.",
            ),
        ])

    async def on_read_resource(ctx, params) -> ReadResourceResult:
        uri = params.uri
        result = await registry.call_tool("get_sdmx_data", parse_csv_uri(uri))
        if not isinstance(result, dict) or not isinstance(result.get("csv"), str):
            raise ValueError(f"No CSV for {uri}: {result}")
        return ReadResourceResult(contents=[TextResourceContents(uri=uri, mime_type=MIME, text=result["csv"])])

    return {
        "on_list_resources": on_list_resources,
        "on_list_resource_templates": on_list_resource_templates,
        "on_read_resource": on_read_resource,
    }

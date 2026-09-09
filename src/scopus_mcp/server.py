import asyncio
import json
import logging
from typing import Any

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from .client import ScopusClient
from .utils import (
    clean_abstract_details,
    clean_search_results,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scopus-mcp")

server = Server("scopus-mcp")
_client: ScopusClient | None = None


def get_client() -> ScopusClient:
    """Create the API client only when a tool is called.

    This keeps the HTTP endpoint available for MCP discovery even when the
    deployment has not yet been configured with a Scopus API key.
    """
    global _client
    if _client is None:
        _client = ScopusClient()
    return _client


def _text_result(value: Any) -> list[types.TextContent]:
    return [types.TextContent(type="text", text=json.dumps(value, ensure_ascii=False, indent=2))]


def _count(arguments: dict[str, Any]) -> int:
    count = arguments.get("count", 5)
    if not isinstance(count, int) or isinstance(count, bool) or not 1 <= count <= 25:
        raise ValueError("count must be an integer between 1 and 25")
    return count


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="search_scopus",
            description="Search Scopus publications using Scopus advanced query syntax.",
            inputSchema={"type": "object", "properties": {
                "query": {"type": "string", "description": "For example: TITLE(machine learning) AND PUBYEAR > 2020."},
                "count": {"type": "integer", "default": 5, "minimum": 1, "maximum": 25},
                "sort": {"type": "string", "default": "coverDate"},
            }, "required": ["query"]},
        ),
        types.Tool(
            name="abstract_retrieval",
            description="Retrieve detailed metadata and the actual abstract text for a Scopus document.",
            inputSchema={"type": "object", "properties": {
                "id_type": {"type": "string", "enum": ["scopus_id", "eid", "doi", "pii", "pubmed_id"], "description": "The type of identifier used for lookup."},
                "id_value": {"type": "string", "description": "For example, DOI 10.1016/j.jclepro.2020.121092 or Scopus ID 85028623301."},
                "view": {"type": "string", "enum": ["META", "META_ABS", "FULL", "REF", "ENTITLED"], "default": "META_ABS", "description": "META_ABS includes metadata and abstract text."},
                "field": {"type": "string", "description": "Optional comma-separated list of response fields."},
            }, "required": ["id_type", "id_value"]},
        ),
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any] | None) -> list[types.TextContent]:
    arguments = arguments or {}
    try:
        if name == "search_scopus":
            query = arguments.get("query")
            if not isinstance(query, str) or not query.strip():
                raise ValueError("query is required")
            count = _count(arguments)
            data = await get_client().search_scopus(query, count=count, sort=arguments.get("sort", "coverDate"))
            return _text_result(clean_search_results(data))

        if name == "abstract_retrieval":
            id_type = arguments.get("id_type")
            id_value = arguments.get("id_value")
            valid_id_types = {"scopus_id", "eid", "doi", "pii", "pubmed_id"}
            if id_type not in valid_id_types:
                raise ValueError("id_type must be one of: scopus_id, eid, doi, pii, pubmed_id")
            if not isinstance(id_value, str) or not id_value.strip():
                raise ValueError("id_value is required")
            view = arguments.get("view", "META_ABS")
            if view not in {"META", "META_ABS", "FULL", "REF", "ENTITLED"}:
                raise ValueError("view must be one of: META, META_ABS, FULL, REF, ENTITLED")
            field = arguments.get("field")
            if field is not None and not isinstance(field, str):
                raise ValueError("field must be a string")
            data = await get_client().get_abstract(id_type, id_value, view=view, field=field)
            return _text_result(clean_abstract_details(data))

        raise ValueError(f"Unknown tool: {name}")
    except Exception as exc:
        logger.exception("Error executing tool %s", name)
        return _text_result({"error": str(exc)})


async def main() -> None:
    try:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())
    finally:
        if _client is not None:
            await _client.close()


def start() -> None:
    """Entry point for local stdio MCP clients."""
    asyncio.run(main())


if __name__ == "__main__":
    start()

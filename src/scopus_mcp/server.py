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
    clean_author_profile,
    clean_author_search_results,
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
            name="get_abstract",
            description="Retrieve a publication's abstract and metadata by Scopus ID or DOI.",
            inputSchema={"type": "object", "properties": {
                "identifier": {"type": "string", "description": "A Scopus ID or DOI."},
            }, "required": ["identifier"]},
        ),
        types.Tool(
            name="get_author_info",
            description="Retrieve an author's Scopus profile, citation metrics, and affiliation by Author ID.",
            inputSchema={"type": "object", "properties": {
                "author_id": {"type": "string"},
            }, "required": ["author_id"]},
        ),
        types.Tool(
            name="search_authors",
            description="Search Scopus author profiles by author name.",
            inputSchema={"type": "object", "properties": {
                "author_name": {"type": "string"},
                "count": {"type": "integer", "default": 5, "minimum": 1, "maximum": 25},
            }, "required": ["author_name"]},
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

        if name == "get_abstract":
            identifier = arguments.get("identifier")
            if not isinstance(identifier, str) or not identifier.strip():
                raise ValueError("identifier is required")
            return _text_result(clean_abstract_details(await get_client().get_abstract(identifier)))

        if name == "get_author_info":
            author_id = arguments.get("author_id")
            if not isinstance(author_id, str) or not author_id.strip():
                raise ValueError("author_id is required")
            return _text_result(clean_author_profile(await get_client().get_author(author_id)))

        if name == "search_authors":
            author_name = arguments.get("author_name")
            if not isinstance(author_name, str) or not author_name.strip():
                raise ValueError("author_name is required")
            count = _count(arguments)
            return _text_result(clean_author_search_results(await get_client().search_authors(author_name, count=count)))

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

"""ASGI application for the unauthenticated Vercel MCP endpoint."""
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from .server import server

session_manager = StreamableHTTPSessionManager(
    server,
    json_response=True,
    stateless=True,
)


@asynccontextmanager
async def lifespan(_: Starlette) -> AsyncIterator[None]:
    async with session_manager.run():
        yield


async def health(_: Request) -> JSONResponse:
    return JSONResponse({"service": "scopus-mcp", "status": "ok", "mcp_endpoint": "/mcp"})


class MCPASGIApp:
    """ASGI route adapter that preserves the exact `/mcp` URL (no redirect)."""

    async def __call__(self, scope: object, receive: object, send: object) -> None:
        await session_manager.handle_request(scope, receive, send)  # type: ignore[arg-type]


app = Starlette(
    routes=[Route("/", health), Route("/mcp", endpoint=MCPASGIApp())],
    lifespan=lifespan,
)

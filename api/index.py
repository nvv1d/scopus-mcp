"""Vercel Python entry point exposing the MCP ASGI application."""
from scopus_mcp.http_app import app

__all__ = ["app"]

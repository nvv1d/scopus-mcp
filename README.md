# Scopus MCP Server (Vercel Deployment)

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that provides unauthenticated, remote access to the Elsevier Scopus API for academic research queries. Deploy it to Vercel and connect an MCP client to `https://<your-deployment>.vercel.app/mcp`.

> The MCP endpoint itself does **not** require OAuth or any other client authentication. The server does require a Scopus API key, which remains private in Vercel's environment variables.

## Deploy to Vercel

1. Fork or push this repository to a Git provider connected to Vercel.
2. Import the repository into Vercel. The included `vercel.json` routes `/mcp` to the Python ASGI function.
3. In **Project Settings → Environment Variables**, add:

   | Name | Value |
   | --- | --- |
   | `SCOPUS_API_KEY` | Your Elsevier Scopus API key |

4. Deploy. Your MCP endpoint is `https://<your-deployment>.vercel.app/mcp`.

The API key is only sent by the server to Elsevier; do not put it in MCP client configuration or request headers.

The server automatically falls back to Vercel's writable temporary directory for its response cache when the runtime home directory is read-only. Set `SCOPUS_MCP_CACHE_DIR` only if you need to use a different writable cache location.

## Tools

The server exposes four MCP tools:

1. **`search_scopus`** — Search publications with Scopus advanced query syntax. Returns titles, authors, journals, citation counts, DOIs, and links.
   - `query` (required), `count` (1–25, default 5), `sort` (default `coverDate`)
2. **`get_abstract`** — Retrieve an abstract and metadata by Scopus ID or DOI.
   - `identifier` (required)
3. **`get_author_info`** — Retrieve an author profile, including publication and citation metrics, h-index when returned by Scopus, and current affiliation.
   - `author_id` (required)
4. **`search_authors`** — Search author profiles by name.
   - `author_name` (required), `count` (1–25, default 5)

## Direct API Testing

No `Authorization` header is required for these calls.

```bash
# List available tools
curl -X POST https://your-deployment.vercel.app/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'

# Search publications
curl -X POST https://your-deployment.vercel.app/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json' \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"search_scopus","arguments":{"query":"TITLE(machine learning) AND PUBYEAR > 2020","count":5}}}'

# Search author profiles
curl -X POST https://your-deployment.vercel.app/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json' \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"search_authors","arguments":{"author_name":"Einstein","count":3}}}'
```

## Scopus Query Syntax

Common field codes include:

- `TITLE()` — search titles.
- `AUTHOR-NAME()` — search author names.
- `AFFIL()` — search affiliations.
- `PUBYEAR` — publication year.
- `DOCTYPE()` — document type, such as `ar` (article), `re` (review), or `cp` (conference paper).
- `SUBJAREA()` — subject area.

Examples:

```text
TITLE(deep learning) AND PUBYEAR > 2020
AUTHOR-NAME(Smith) AND AFFIL(MIT)
TITLE-ABS-KEY(cancer treatment) AND DOCTYPE(ar)
```

## Local development

```bash
uv sync --extra dev
uv run pytest
```

For local stdio MCP use, set `SCOPUS_API_KEY` and run `uv run scopus-mcp`.

## API limits

Scopus API rate limits depend on your subscription tier. Search requests are limited to 25 results per request, and institutional access may be needed for full text.

## License

[MIT](LICENSE)

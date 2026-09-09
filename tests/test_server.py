import json
import unittest
from unittest.mock import AsyncMock, patch

from starlette.testclient import TestClient

from scopus_mcp.http_app import app
from scopus_mcp.server import handle_call_tool, handle_list_tools


class TestMCPTools(unittest.IsolatedAsyncioTestCase):
    async def test_lists_the_four_remote_tools(self):
        tools = await handle_list_tools()
        self.assertEqual(
            [tool.name for tool in tools],
            ['search_scopus', 'get_abstract', 'get_author_info', 'search_authors'],
        )

    async def test_search_authors_uses_name_and_count(self):
        client = unittest.mock.MagicMock()
        client.search_authors = AsyncMock(return_value={'search-results': {'entry': []}})

        with patch('scopus_mcp.server.get_client', return_value=client):
            result = await handle_call_tool('search_authors', {'author_name': 'Einstein', 'count': 3})

        client.search_authors.assert_awaited_once_with('Einstein', count=3)
        self.assertEqual(json.loads(result[0].text), [])

    async def test_invalid_count_is_returned_as_a_tool_error(self):
        result = await handle_call_tool('search_scopus', {'query': 'TITLE(AI)', 'count': 26})
        self.assertEqual(json.loads(result[0].text), {'error': 'count must be an integer between 1 and 25'})


class TestVercelRoute(unittest.TestCase):
    def test_api_function_route_accepts_mcp_requests(self):
        with TestClient(app) as test_client:
            response = test_client.post(
                '/api',
                headers={'Accept': 'application/json'},
                json={'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list'},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['result']['tools'][0]['name'], 'search_scopus')

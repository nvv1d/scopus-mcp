import json
import unittest
from unittest.mock import AsyncMock, patch

from starlette.testclient import TestClient

from scopus_mcp.http_app import app
from scopus_mcp.server import handle_call_tool, handle_list_tools


class TestMCPTools(unittest.IsolatedAsyncioTestCase):
    async def test_lists_the_search_and_abstract_tools(self):
        tools = await handle_list_tools()
        self.assertEqual(
            [tool.name for tool in tools],
            ['search_scopus', 'abstract_retrieval'],
        )

    async def test_abstract_retrieval_requests_meta_abs_by_default(self):
        client = unittest.mock.MagicMock()
        client.get_abstract = AsyncMock(return_value={
            'abstracts-retrieval-response': {
                'coredata': {'dc:identifier': 'SCOPUS_ID:1'},
                'item': {'bibrecord': {'head': {'abstracts': {'ce:abstract': 'Abstract text.'}}}},
            }
        })

        with patch('scopus_mcp.server.get_client', return_value=client):
            result = await handle_call_tool('abstract_retrieval', {'id_type': 'doi', 'id_value': '10.1000/example'})

        client.get_abstract.assert_awaited_once_with('doi', '10.1000/example', view='META_ABS', field=None)
        self.assertEqual(json.loads(result[0].text)['abstract'], 'Abstract text.')

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
        self.assertEqual(
            [tool['name'] for tool in response.json()['result']['tools']],
            ['search_scopus', 'abstract_retrieval'],
        )

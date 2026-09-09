import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scopus_mcp.cache import CacheManager


class TestCacheManager(unittest.TestCase):
    def test_uses_temp_directory_when_configured_cache_is_read_only(self):
        with patch.object(Path, 'mkdir', side_effect=[OSError(30, 'Read-only file system'), None]):
            cache = CacheManager(cache_dir='/read-only/cache')

        self.assertEqual(cache.cache_dir, Path(tempfile.gettempdir()) / 'scopus-mcp')

    def test_disables_cache_when_no_writable_directory_is_available(self):
        with patch.object(Path, 'mkdir', side_effect=OSError(30, 'Read-only file system')):
            cache = CacheManager(cache_dir='/read-only/cache')

        self.assertIsNone(cache.cache_dir)
        self.assertIsNone(cache.get('https://example.test'))
        cache.set('https://example.test', {'ok': True})

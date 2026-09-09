import json
import hashlib
import os
import tempfile
import time
from pathlib import Path
from typing import Optional, Dict, Any, Union

class CacheManager:
    def __init__(self, cache_dir: Union[str, Path] = None, expiration_seconds: int = 86400):
        self.cache_dir: Optional[Path]
        if cache_dir is None:
            configured_cache_dir = os.getenv('SCOPUS_MCP_CACHE_DIR')
            self.cache_dir = Path(configured_cache_dir) if configured_cache_dir else Path.home() / ".cache" / "scopus-mcp"
        else:
            self.cache_dir = Path(cache_dir).resolve()
        self.expiration_seconds = expiration_seconds
        self._ensure_writable_cache_dir()

    def _ensure_writable_cache_dir(self) -> None:
        """Use a writable temporary directory when HOME is read-only.

        Serverless runtimes, including Vercel, commonly mount the user's home
        directory read-only while allowing writes under the system temp folder.
        Caching is an optimization, so disable it rather than failing an API
        request if neither location can be created.
        """
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            return
        except OSError:
            fallback_dir = Path(tempfile.gettempdir()) / "scopus-mcp"

        try:
            fallback_dir.mkdir(parents=True, exist_ok=True)
            self.cache_dir = fallback_dir
        except OSError:
            self.cache_dir = None

    def _get_cache_key(self, url: str, params: Optional[Dict[str, Any]] = None) -> str:
        """Generates a SHA256 hash key based on URL and sorted parameters."""
        key_str = url
        if params:
            # Sort keys to ensure deterministic hashing
            key_str += json.dumps(params, sort_keys=True, default=str)
        return hashlib.sha256(key_str.encode('utf-8')).hexdigest()

    def get(self, url: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Retrieves data from cache if it exists and is not expired."""
        if self.cache_dir is None:
            return None

        key = self._get_cache_key(url, params)
        file_path = self.cache_dir / f"{key}.json"

        try:
            if not file_path.exists():
                return None
            with open(file_path, 'r', encoding='utf-8') as f:
                cached_entry = json.load(f)
            
            timestamp = cached_entry.get('timestamp', 0)
            ttl = cached_entry.get('ttl', self.expiration_seconds) # Use stored TTL or default
            
            if time.time() - timestamp > ttl:
                return None # Expired
            
            return cached_entry.get('data')
        except (json.JSONDecodeError, OSError):
            return None

    def set(self, url: str, data: Any, params: Optional[Dict[str, Any]] = None, ttl: Optional[int] = None) -> None:
        """Saves data to the cache with a timestamp and optional TTL."""
        if self.cache_dir is None:
            return

        key = self._get_cache_key(url, params)
        file_path = self.cache_dir / f"{key}.json"
        
        cache_entry = {
            'timestamp': time.time(),
            'ttl': ttl if ttl is not None else self.expiration_seconds,
            'data': data
        }
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(cache_entry, f, ensure_ascii=False, indent=2)
        except OSError:
            # Silently fail on cache write errors to avoid crashing the app
            pass

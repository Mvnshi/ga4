"""
Caching Utilities
=================
Disk-based caching to avoid redundant API calls.
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Optional, Callable
from functools import wraps
import diskcache

from config.settings import CACHE_DIR, get_settings


class DataCache:
    """
    Disk-based cache for API responses.
    
    Caches are automatically invalidated after TTL expires.
    Different clients have separate cache namespaces.
    """
    
    def __init__(self, client_name: str = "default"):
        self.client_name = client_name
        self.cache_dir = CACHE_DIR / client_name
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache = diskcache.Cache(str(self.cache_dir))
        
        settings = get_settings()
        self.ttl_seconds = settings.cache_ttl_hours * 3600
        self.enabled = settings.cache_enabled
    
    def _make_key(self, *args, **kwargs) -> str:
        """Generate a cache key from arguments."""
        key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from cache."""
        if not self.enabled:
            return None
        return self._cache.get(key)
    
    def set(self, key: str, value: Any, ttl: int = None) -> None:
        """Set a value in cache."""
        if not self.enabled:
            return
        ttl = ttl or self.ttl_seconds
        self._cache.set(key, value, expire=ttl)
    
    def delete(self, key: str) -> None:
        """Delete a key from cache."""
        self._cache.delete(key)
    
    def clear(self) -> None:
        """Clear all cached data for this client."""
        self._cache.clear()
    
    def get_stats(self) -> dict:
        """Get cache statistics."""
        return {
            "size": len(self._cache),
            "volume": self._cache.volume(),
            "client": self.client_name
        }


def cached(ttl_hours: int = None):
    """
    Decorator to cache function results.
    
    Usage:
        @cached(ttl_hours=24)
        def fetch_data(start_date, end_date):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Get client name from self if available
            client_name = getattr(self, 'client_name', 'default')
            cache = DataCache(client_name)
            
            # Generate cache key
            key = cache._make_key(func.__name__, *args, **kwargs)
            
            # Try to get from cache
            cached_value = cache.get(key)
            if cached_value is not None:
                return cached_value
            
            # Execute function and cache result
            result = func(self, *args, **kwargs)
            
            ttl = (ttl_hours or get_settings().cache_ttl_hours) * 3600
            cache.set(key, result, ttl=ttl)
            
            return result
        return wrapper
    return decorator


def clear_client_cache(client_name: str) -> None:
    """Clear all cached data for a specific client."""
    cache = DataCache(client_name)
    cache.clear()
    print(f"✓ Cleared cache for client: {client_name}")


def clear_all_cache() -> None:
    """Clear all cached data."""
    import shutil
    if CACHE_DIR.exists():
        shutil.rmtree(CACHE_DIR)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
    print("✓ Cleared all cache data")


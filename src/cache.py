"""
Cache module for storing frequently accessed data.
"""

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional, Set, List, Union

from sqlitedict import SqliteDict

from src.config import (
    CACHE_DIRECTORY,
    METADATA_CACHE_MAX_SIZE,
    DATA_CACHE_MAX_SIZE,
    CACHE_EXPIRY_SECONDS,
)

logger = logging.getLogger(__name__)

class Cache:
    """Simple cache for storing frequently accessed data."""
    
    def __init__(
        self,
        name: str,
        cache_dir: Path = CACHE_DIRECTORY,
        max_size: int = 1000,
        expiry_seconds: int = CACHE_EXPIRY_SECONDS,
    ):
        """Initialize the cache.
        
        Args:
            name: Cache name (used for the filename)
            cache_dir: Directory to store cache files
            max_size: Maximum number of items to store
            expiry_seconds: Time in seconds before entries expire
        """
        self.name = name
        self.cache_dir = cache_dir
        self.max_size = max_size
        self.expiry_seconds = expiry_seconds
        self.in_memory_only = False
        
        try:
            # Ensure cache directory exists
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            
            self.db_path = self.cache_dir / f"{name}.sqlite"
            self.cache = SqliteDict(str(self.db_path), autocommit=True)
            
            # Keep track of access times for LRU eviction
            self.access_times: Dict[str, float] = {}
            
            logger.info(f"Initialized cache '{name}' at {self.db_path}")
            self._load_access_times()
        except Exception as e:
            import sys
            print(f"Error initializing cache '{name}': {e}", file=sys.stderr)
            print(f"Falling back to in-memory cache for '{name}'", file=sys.stderr)
            
            # Fallback to in-memory dictionary
            self.cache = {}
            self.access_times = {}
            self.in_memory_only = True
            logger.warning(f"Using in-memory cache for '{name}' due to error: {e}")
    
    def _load_access_times(self):
        """Load access times from the cache."""
        for key in self.cache.keys():
            if not key.startswith("__"):  # Skip metadata keys
                self.access_times[key] = time.time()
    
    def _evict_if_needed(self):
        """Evict least recently used items if cache exceeds max size."""
        if len(self.cache) > self.max_size:
            # Sort by access time (oldest first)
            items_to_evict = sorted(
                self.access_times.items(), key=lambda x: x[1]
            )[:(len(self.cache) - self.max_size)]
            
            for key, _ in items_to_evict:
                logger.debug(f"Evicting '{key}' from cache '{self.name}'")
                del self.cache[key]
                del self.access_times[key]
    
    def _check_expiry(self, key: str, value: Dict[str, Any]) -> bool:
        """Check if a cache entry has expired.
        
        Args:
            key: Cache key
            value: Cached value with metadata
            
        Returns:
            True if the entry has expired, False otherwise
        """
        if "__timestamp__" not in value:
            return True
        
        timestamp = value["__timestamp__"]
        age = time.time() - timestamp
        
        if age > self.expiry_seconds:
            logger.debug(f"Cache entry '{key}' has expired (age: {age:.2f}s)")
            return True
        
        return False
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found or expired
        """
        if key not in self.cache:
            return None
        
        value = self.cache[key]
        
        # Check if expired
        if self._check_expiry(key, value):
            del self.cache[key]
            if key in self.access_times:
                del self.access_times[key]
            return None
        
        # Update access time
        self.access_times[key] = time.time()
        
        logger.debug(f"Cache hit for '{key}' in cache '{self.name}'")
        return value["__data__"]
    
    def set(self, key: str, value: Any):
        """Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        self.cache[key] = {
            "__timestamp__": time.time(),
            "__data__": value,
        }
        
        self.access_times[key] = time.time()
        logger.debug(f"Cached '{key}' in cache '{self.name}'")
        
        self._evict_if_needed()
    
    def delete(self, key: str):
        """Delete a value from the cache.
        
        Args:
            key: Cache key
        """
        if key in self.cache:
            del self.cache[key]
        
        if key in self.access_times:
            del self.access_times[key]
        
        logger.debug(f"Deleted '{key}' from cache '{self.name}'")
    
    def clear(self):
        """Clear all entries from the cache."""
        self.cache.clear()
        self.access_times.clear()
        logger.info(f"Cleared cache '{self.name}'")
    
    def close(self):
        """Close the cache."""
        if not self.in_memory_only and hasattr(self.cache, 'close'):
            self.cache.close()
        logger.info(f"Closed cache '{self.name}'")
    
    def keys(self) -> List[str]:
        """Get all keys in the cache.
        
        Returns:
            List of cache keys
        """
        return [k for k in self.cache.keys() if not k.startswith("__")]
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Create caches for different types of data
metadata_cache = Cache("metadata", max_size=METADATA_CACHE_MAX_SIZE)
data_cache = Cache("data", max_size=DATA_CACHE_MAX_SIZE)


def get_cached_or_fetch(cache: Cache, key: str, fetch_func, *args, **kwargs):
    """Get a value from cache or fetch it if not available.
    
    Args:
        cache: Cache to use
        key: Cache key
        fetch_func: Function to call if value is not in cache
        *args: Arguments to pass to fetch_func
        **kwargs: Keyword arguments to pass to fetch_func
        
    Returns:
        Cached or freshly fetched value
    """
    value = cache.get(key)
    
    if value is None:
        logger.debug(f"Cache miss for '{key}', fetching fresh data")
        value = fetch_func(*args, **kwargs)
        cache.set(key, value)
    
    return value
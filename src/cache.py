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
    SEARCH_CACHE_MAX_SIZE,
    SEARCH_CACHE_EXPIRY_SECONDS,
    VECTOR_CACHE_MAX_SIZE,
    VECTOR_CACHE_EXPIRY_SECONDS,
    CUBE_CACHE_MAX_SIZE,
    CUBE_CACHE_EXPIRY_SECONDS,
    HOT_CACHE_VECTORS,
    HOT_CACHE_CUBES,
    PRELOAD_HOT_CACHE,
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

# Create specialized caches for different data types
search_cache = Cache("search", max_size=SEARCH_CACHE_MAX_SIZE, expiry_seconds=SEARCH_CACHE_EXPIRY_SECONDS)
vector_cache = Cache("vector", max_size=VECTOR_CACHE_MAX_SIZE, expiry_seconds=VECTOR_CACHE_EXPIRY_SECONDS)
cube_cache = Cache("cube", max_size=CUBE_CACHE_MAX_SIZE, expiry_seconds=CUBE_CACHE_EXPIRY_SECONDS)

# Dictionary to store the last access time for hot cache items
hot_cache_access_times = {}


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

async def get_cached_or_fetch_async(cache: Cache, key: str, fetch_func, *args, **kwargs):
    """Async version of get_cached_or_fetch.
    
    Args:
        cache: Cache to use
        key: Cache key
        fetch_func: Async function to call if value is not in cache
        *args: Arguments to pass to fetch_func
        **kwargs: Keyword arguments to pass to fetch_func
        
    Returns:
        Cached or freshly fetched value
    """
    value = cache.get(key)
    
    if value is None:
        logger.debug(f"Cache miss for '{key}', fetching fresh data")
        value = await fetch_func(*args, **kwargs)
        cache.set(key, value)
    
    return value

def is_hot_cache_item(item_type: str, item_id: str) -> bool:
    """Check if an item should be hot-cached.
    
    Args:
        item_type: Type of item ('vector' or 'cube')
        item_id: ID of the item
        
    Returns:
        True if the item should be hot-cached, False otherwise
    """
    if item_type == 'vector':
        # Clean the vector ID for comparison (remove 'v' prefix if present)
        clean_id = item_id.lower().replace('v', '') if isinstance(item_id, str) else str(item_id)
        return any(v.lower().replace('v', '') == clean_id for v in HOT_CACHE_VECTORS)
    elif item_type == 'cube':
        # Clean the cube ID for comparison (use first 8 digits)
        clean_id = str(item_id)
        if len(clean_id) == 10:
            clean_id = clean_id[:8]
        return any(c == clean_id for c in HOT_CACHE_CUBES)
    else:
        return False

def update_hot_cache_access(item_type: str, item_id: str):
    """Update the access time for a hot cache item.
    
    Args:
        item_type: Type of item ('vector' or 'cube')
        item_id: ID of the item
    """
    if is_hot_cache_item(item_type, item_id):
        key = f"{item_type}:{item_id}"
        hot_cache_access_times[key] = time.time()
        logger.debug(f"Updated hot cache access time for {key}")

async def get_vector_data_cached(client, vector: str, n_periods: int = 10, force_refresh: bool = False):
    """Get vector data with caching.
    
    Args:
        client: WDS client
        vector: Vector ID
        n_periods: Number of periods to retrieve
        force_refresh: Force refresh from API
        
    Returns:
        Vector data
    """
    # Clean the vector ID for caching
    clean_vector = vector.lower().replace('v', '') if isinstance(vector, str) else str(vector)
    cache_key = f"vector:{clean_vector}:{n_periods}"
    
    # Check if it's a hot cache item
    is_hot = is_hot_cache_item('vector', vector)
    
    # Use the appropriate cache
    if is_hot:
        # For hot items, we still use the vector cache but with special handling
        update_hot_cache_access('vector', vector)
        
    # Get from cache or fetch from API
    if force_refresh:
        data = await client.get_data_from_vectors([vector], n_periods)
        vector_cache.set(cache_key, data)
        return data
    else:
        return await get_cached_or_fetch_async(vector_cache, cache_key, 
                                              client.get_data_from_vectors, [vector], n_periods)

async def get_cube_metadata_cached(client, product_id: str, force_refresh: bool = False):
    """Get cube metadata with caching.
    
    Args:
        client: WDS client
        product_id: Product ID
        force_refresh: Force refresh from API
        
    Returns:
        Cube metadata
    """
    # Clean the product ID for caching
    clean_pid = str(product_id)
    if len(clean_pid) == 10:
        clean_pid = clean_pid[:8]
    
    cache_key = f"cube:{clean_pid}"
    
    # Check if it's a hot cache item
    is_hot = is_hot_cache_item('cube', product_id)
    
    # Use the appropriate cache
    if is_hot:
        # For hot items, update access time
        update_hot_cache_access('cube', product_id)
        
    # Get from cache or fetch from API
    if force_refresh:
        data = await client.get_cube_metadata(product_id)
        cube_cache.set(cache_key, data)
        return data
    else:
        return await get_cached_or_fetch_async(cube_cache, cache_key, 
                                              client.get_cube_metadata, product_id)

async def get_search_results_cached(client, search_text: str, force_refresh: bool = False):
    """Get search results with caching.
    
    Args:
        client: WDS client
        search_text: Search text
        force_refresh: Force refresh from API
        
    Returns:
        Search results
    """
    # Create a consistent cache key
    clean_search = search_text.lower().strip()
    cache_key = f"search:{clean_search}"
    
    # Get from cache or fetch from API
    if force_refresh:
        data = await client.search_cubes(search_text)
        search_cache.set(cache_key, data)
        return data
    else:
        return await get_cached_or_fetch_async(search_cache, cache_key, 
                                              client.search_cubes, search_text)

async def preload_hot_cache(client):
    """Preload hot cache items.
    
    Args:
        client: WDS client
    """
    if not PRELOAD_HOT_CACHE:
        return
    
    logger.info("Preloading hot cache items...")
    
    # Preload hot vectors
    for vector in HOT_CACHE_VECTORS:
        try:
            await get_vector_data_cached(client, vector, 20, force_refresh=True)
            logger.debug(f"Preloaded vector {vector}")
        except Exception as e:
            logger.error(f"Error preloading vector {vector}: {e}")
    
    # Preload hot cubes
    for cube in HOT_CACHE_CUBES:
        try:
            await get_cube_metadata_cached(client, cube, force_refresh=True)
            logger.debug(f"Preloaded cube {cube}")
        except Exception as e:
            logger.error(f"Error preloading cube {cube}: {e}")
    
    logger.info("Hot cache preloading completed")
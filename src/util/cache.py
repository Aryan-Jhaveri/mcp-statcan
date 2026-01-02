# Cube cache module for StatCan MCP Server
# Caches the cube list to avoid repeated API calls

import time
from typing import List, Dict, Any, Optional
from ..util.logger import log_server_debug

# Global cache storage
_CUBE_CACHE: Optional[List[Dict[str, Any]]] = None
_CACHE_TIMESTAMP: Optional[float] = None
_CACHE_TTL_SECONDS: float = 3600.0  # 1 hour cache TTL

async def get_cached_cubes_list_lite(fetch_func) -> List[Dict[str, Any]]:
    """
    Returns cached cube list if available and fresh, otherwise fetches and caches.
    
    Args:
        fetch_func: Async function to fetch cube list when cache is stale
        
    Returns:
        List of cube dictionaries in lite format
    """
    global _CUBE_CACHE, _CACHE_TIMESTAMP
    
    current_time = time.time()
    
    # Check if cache is valid
    if _CUBE_CACHE is not None and _CACHE_TIMESTAMP is not None:
        cache_age = current_time - _CACHE_TIMESTAMP
        if cache_age < _CACHE_TTL_SECONDS:
            log_server_debug(f"Using cached cube list (age: {cache_age:.1f}s, {len(_CUBE_CACHE)} cubes)")
            return _CUBE_CACHE
        else:
            log_server_debug(f"Cache expired (age: {cache_age:.1f}s > TTL: {_CACHE_TTL_SECONDS}s)")
    
    # Fetch fresh data
    log_server_debug("Fetching fresh cube list from API...")
    start_time = time.time()
    _CUBE_CACHE = await fetch_func()
    _CACHE_TIMESTAMP = time.time()
    elapsed = _CACHE_TIMESTAMP - start_time
    log_server_debug(f"Cached {len(_CUBE_CACHE)} cubes in {elapsed:.2f}s")
    
    return _CUBE_CACHE

def invalidate_cache():
    """Manually invalidate the cube cache."""
    global _CUBE_CACHE, _CACHE_TIMESTAMP
    _CUBE_CACHE = None
    _CACHE_TIMESTAMP = None
    log_server_debug("Cube cache invalidated")

def get_cache_stats() -> Dict[str, Any]:
    """Return cache statistics for debugging."""
    global _CUBE_CACHE, _CACHE_TIMESTAMP
    
    if _CUBE_CACHE is None:
        return {"cached": False, "count": 0, "age_seconds": None}
    
    age = time.time() - _CACHE_TIMESTAMP if _CACHE_TIMESTAMP else None
    return {
        "cached": True,
        "count": len(_CUBE_CACHE),
        "age_seconds": round(age, 1) if age else None,
        "ttl_seconds": _CACHE_TTL_SECONDS,
        "expires_in": round(_CACHE_TTL_SECONDS - age, 1) if age else None
    }

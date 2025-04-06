#!/usr/bin/env python3
"""
Script to test the enhanced StatCan caching system.

This script tests the different cache types and tiered caching approach.

Run with: python scripts/cache_test.py
"""

import asyncio
import logging
import sys
import time
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.cache import (
    search_cache, vector_cache, cube_cache, metadata_cache,
    get_vector_data_cached, get_cube_metadata_cached, get_search_results_cached,
    preload_hot_cache, is_hot_cache_item
)
from src.config import HOT_CACHE_VECTORS, HOT_CACHE_CUBES
from src.wds_client import WDSClient

# Configure logging to console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr),
    ]
)

logger = logging.getLogger(__name__)

async def test_basic_cache():
    """Test basic cache operations."""
    print("\n=== Testing Basic Cache Operations ===")
    
    # Try storing and retrieving some test data
    print("Testing metadata cache...")
    test_key = "test:metadata"
    test_value = {"status": "SUCCESS", "object": {"test": "data"}}
    
    # Store in cache
    metadata_cache.set(test_key, test_value)
    
    # Retrieve from cache
    retrieved = metadata_cache.get(test_key)
    
    if retrieved == test_value:
        print("✅ Metadata cache test passed")
    else:
        print(f"❌ Metadata cache test failed: {retrieved} != {test_value}")
    
    # Test cache clearing
    print("\nTesting cache clearing...")
    metadata_cache.clear()
    
    # Try to retrieve the cleared key
    retrieved = metadata_cache.get(test_key)
    
    if retrieved is None:
        print("✅ Cache clearing test passed")
    else:
        print(f"❌ Cache clearing test failed: {retrieved} is not None")

async def test_specialized_caches():
    """Test the specialized cache types."""
    print("\n=== Testing Specialized Cache Types ===")
    
    client = WDSClient()
    try:
        # Test search cache
        print("\nTesting search cache...")
        search_term = "inflation"
        
        # First fetch (cache miss)
        start = time.time()
        result1 = await get_search_results_cached(client, search_term)
        time1 = time.time() - start
        
        # Second fetch (should be cache hit)
        start = time.time()
        result2 = await get_search_results_cached(client, search_term)
        time2 = time.time() - start
        
        # Check results
        if result1 == result2:
            print(f"✅ Search cache test passed")
            print(f"   First fetch: {time1:.3f}s, Second fetch: {time2:.3f}s")
            if time2 < time1:
                print(f"   Performance improvement: {time1/time2:.1f}x faster with cache")
        else:
            print(f"❌ Search cache test failed: results differ")
        
        # Test vector cache
        print("\nTesting vector cache...")
        vector = "v41690973"  # CPI All-items
        
        # First fetch (cache miss)
        start = time.time()
        vector_result1 = await get_vector_data_cached(client, vector, 5)
        time1 = time.time() - start
        
        # Second fetch (should be cache hit)
        start = time.time()
        vector_result2 = await get_vector_data_cached(client, vector, 5)
        time2 = time.time() - start
        
        # Check results
        if vector_result1 == vector_result2:
            print(f"✅ Vector cache test passed")
            print(f"   First fetch: {time1:.3f}s, Second fetch: {time2:.3f}s")
            if time2 < time1:
                print(f"   Performance improvement: {time1/time2:.1f}x faster with cache")
        else:
            print(f"❌ Vector cache test failed: results differ")
        
        # Test cube cache
        print("\nTesting cube cache...")
        cube = "1810000401"  # CPI table
        
        # First fetch (cache miss)
        start = time.time()
        cube_result1 = await get_cube_metadata_cached(client, cube)
        time1 = time.time() - start
        
        # Second fetch (should be cache hit)
        start = time.time()
        cube_result2 = await get_cube_metadata_cached(client, cube)
        time2 = time.time() - start
        
        # Check results
        if cube_result1 == cube_result2:
            print(f"✅ Cube cache test passed")
            print(f"   First fetch: {time1:.3f}s, Second fetch: {time2:.3f}s")
            if time2 < time1:
                print(f"   Performance improvement: {time1/time2:.1f}x faster with cache")
        else:
            print(f"❌ Cube cache test failed: results differ")
        
    finally:
        await client.close()

async def test_hot_cache():
    """Test the hot cache system."""
    print("\n=== Testing Hot Cache System ===")
    
    # Test hot cache item detection
    print("\nTesting hot cache item detection...")
    
    # Vector tests
    for vector in ["v41690973", "41690973", "V41690973"]:
        if is_hot_cache_item("vector", vector):
            print(f"✅ Correctly identified '{vector}' as a hot vector")
        else:
            print(f"❌ Failed to identify '{vector}' as a hot vector")
    
    if not is_hot_cache_item("vector", "v99999999"):
        print(f"✅ Correctly identified 'v99999999' as NOT a hot vector")
    else:
        print(f"❌ Incorrectly identified 'v99999999' as a hot vector")
    
    # Cube tests
    for cube in ["1810000401", "18100004", "1810000401XX"]:
        if is_hot_cache_item("cube", cube):
            print(f"✅ Correctly identified '{cube}' as a hot cube")
        else:
            print(f"❌ Failed to identify '{cube}' as a hot cube")
    
    if not is_hot_cache_item("cube", "9999999999"):
        print(f"✅ Correctly identified '9999999999' as NOT a hot cube")
    else:
        print(f"❌ Incorrectly identified '9999999999' as a hot cube")
    
    # Test preloading
    print("\nTesting hot cache preloading...")
    client = WDSClient()
    
    try:
        # Clear caches first
        vector_cache.clear()
        cube_cache.clear()
        
        # Preload hot cache items
        await preload_hot_cache(client)
        
        # Check if hot items were cached
        for vector in HOT_CACHE_VECTORS:
            clean_vector = vector.lower().replace('v', '')
            cache_key = f"vector:{clean_vector}:20"
            
            value = vector_cache.get(cache_key)
            if value is not None:
                print(f"✅ Vector {vector} was preloaded in cache")
            else:
                print(f"❌ Vector {vector} was NOT preloaded in cache")
        
        for cube in HOT_CACHE_CUBES:
            clean_cube = str(cube)
            if len(clean_cube) == 10:
                clean_cube = clean_cube[:8]
            
            cache_key = f"cube:{clean_cube}"
            
            value = cube_cache.get(cache_key)
            if value is not None:
                print(f"✅ Cube {cube} was preloaded in cache")
            else:
                print(f"❌ Cube {cube} was NOT preloaded in cache")
        
    finally:
        await client.close()

async def test_cache_performance():
    """Test cache performance with concurrent requests."""
    print("\n=== Testing Cache Performance with Concurrent Requests ===")
    
    client = WDSClient()
    
    try:
        # Clear caches first
        vector_cache.clear()
        
        vector = "v41690973"  # CPI All-items
        
        # First, do a single request to prime the cache
        print("\nPriming cache...")
        await get_vector_data_cached(client, vector, 10)
        
        # Test concurrent uncached requests (simulate multiple users)
        print("\nTesting 10 concurrent requests with UNCACHED vectors...")
        # Use different vectors that are not in cache
        uncached_vectors = [f"v{10000000 + i}" for i in range(10)]
        
        start = time.time()
        uncached_tasks = []
        for v in uncached_vectors:
            # Force refresh to bypass cache
            uncached_tasks.append(get_vector_data_cached(client, v, 5, force_refresh=True))
        
        # Wait for all tasks to complete
        uncached_results = await asyncio.gather(*uncached_tasks, return_exceptions=True)
        uncached_time = time.time() - start
        
        print(f"Completed 10 uncached requests in {uncached_time:.3f}s")
        
        # Test concurrent cached requests (simulate multiple users)
        print("\nTesting 10 concurrent requests with CACHED vector...")
        
        start = time.time()
        cached_tasks = []
        for _ in range(10):
            cached_tasks.append(get_vector_data_cached(client, vector, 10))
        
        # Wait for all tasks to complete
        cached_results = await asyncio.gather(*cached_tasks)
        cached_time = time.time() - start
        
        print(f"Completed 10 cached requests in {cached_time:.3f}s")
        
        # Compare performance
        if cached_time < uncached_time:
            print(f"✅ Cache performance test passed: {uncached_time/cached_time:.1f}x faster with cache")
        else:
            print(f"❌ Cache performance test failed: cached requests not faster")
        
    finally:
        await client.close()

async def main():
    """Run all tests."""
    print("Starting StatCan cache system tests...")
    
    try:
        # Test basic cache operations
        await test_basic_cache()
        
        # Test specialized caches
        await test_specialized_caches()
        
        # Test hot cache system
        await test_hot_cache()
        
        # Test cache performance
        await test_cache_performance()
        
        print("\n✅ All cache tests completed!")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n❌ Error during testing: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
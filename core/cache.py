"""
Response caching for Local Brain.
Caches AI responses to avoid duplicate API calls.
"""
import hashlib
import json
import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from core.logger import logger

# Cache storage: {cache_key: {response: str, timestamp: float, hits: int}}
_cache: Dict[str, Dict[str, Any]] = {}

# Default TTL (Time To Live) in seconds
DEFAULT_TTL = 3600  # 1 hour

# Cache statistics
_cache_stats = {
    "hits": 0,
    "misses": 0,
    "total_requests": 0,
    "cache_size": 0,
    "evictions": 0
}

def generate_cache_key(prompt: str, model_name: str, temperature: Optional[float] = None, 
                       max_tokens: Optional[int] = None, **kwargs) -> str:
    """
    Generate a cache key from prompt and parameters.
    
    Args:
        prompt: The prompt text
        model_name: Model name
        temperature: Temperature parameter (optional)
        max_tokens: Max tokens parameter (optional)
        **kwargs: Additional parameters
    
    Returns:
        Cache key string
    """
    # Create a string representation of all parameters
    params = {
        "prompt": prompt,
        "model": model_name,
        "temperature": temperature,
        "max_tokens": max_tokens,
        **kwargs
    }
    
    # Sort keys for consistency
    params_str = json.dumps(params, sort_keys=True, ensure_ascii=False)
    
    # Generate hash
    cache_key = hashlib.sha256(params_str.encode('utf-8')).hexdigest()
    return cache_key

def get_cached_response(cache_key: str, ttl: int = DEFAULT_TTL) -> Optional[str]:
    """
    Get cached response if available and not expired.
    
    Args:
        cache_key: Cache key
        ttl: Time to live in seconds
    
    Returns:
        Cached response or None if not found/expired
    """
    _cache_stats["total_requests"] += 1
    
    if cache_key not in _cache:
        _cache_stats["misses"] += 1
        logger.debug(f"Cache miss for key: {cache_key[:16]}...")
        return None
    
    cache_entry = _cache[cache_key]
    timestamp = cache_entry.get("timestamp", 0)
    age = time.time() - timestamp
    
    # Check if expired
    if age > ttl:
        # Remove expired entry
        del _cache[cache_key]
        _cache_stats["misses"] += 1
        _cache_stats["evictions"] += 1
        _cache_stats["cache_size"] = len(_cache)
        logger.debug(f"Cache entry expired and removed: {cache_key[:16]}...")
        return None
    
    # Cache hit
    _cache_stats["hits"] += 1
    cache_entry["hits"] = cache_entry.get("hits", 0) + 1
    logger.debug(f"Cache hit for key: {cache_key[:16]}... (age: {age:.1f}s)")
    return cache_entry["response"]

def cache_response(cache_key: str, response: str, ttl: int = DEFAULT_TTL):
    """
    Cache a response.
    
    Args:
        cache_key: Cache key
        response: Response to cache
        ttl: Time to live in seconds
    """
    _cache[cache_key] = {
        "response": response,
        "timestamp": time.time(),
        "hits": 0,
        "ttl": ttl
    }
    _cache_stats["cache_size"] = len(_cache)
    logger.debug(f"Cached response for key: {cache_key[:16]}... (TTL: {ttl}s)")

def clear_cache():
    """Clear all cache entries."""
    global _cache
    cleared_count = len(_cache)
    _cache.clear()
    _cache_stats["cache_size"] = 0
    logger.info(f"Cache cleared: {cleared_count} entries removed")

def clear_expired_entries(ttl: int = DEFAULT_TTL):
    """Remove expired cache entries."""
    current_time = time.time()
    expired_keys = []
    
    for key, entry in _cache.items():
        timestamp = entry.get("timestamp", 0)
        age = current_time - timestamp
        if age > ttl:
            expired_keys.append(key)
    
    for key in expired_keys:
        del _cache[key]
        _cache_stats["evictions"] += 1
    
    _cache_stats["cache_size"] = len(_cache)
    
    if expired_keys:
        logger.info(f"Cleared {len(expired_keys)} expired cache entries")
    
    return len(expired_keys)

def get_cache_stats() -> Dict[str, Any]:
    """
    Get cache statistics.
    
    Returns:
        Dictionary with cache statistics
    """
    hit_rate = 0.0
    if _cache_stats["total_requests"] > 0:
        hit_rate = _cache_stats["hits"] / _cache_stats["total_requests"]
    
    return {
        "hits": _cache_stats["hits"],
        "misses": _cache_stats["misses"],
        "total_requests": _cache_stats["total_requests"],
        "hit_rate": hit_rate,
        "cache_size": _cache_stats["cache_size"],
        "evictions": _cache_stats["evictions"],
        "entries": [
            {
                "key": key[:16] + "...",
                "hits": entry.get("hits", 0),
                "age_seconds": time.time() - entry.get("timestamp", 0),
                "ttl": entry.get("ttl", DEFAULT_TTL)
            }
            for key, entry in list(_cache.items())[:100]  # Limit to first 100 entries
        ]
    }

def reset_cache_stats():
    """Reset cache statistics."""
    global _cache_stats
    _cache_stats = {
        "hits": 0,
        "misses": 0,
        "total_requests": 0,
        "cache_size": len(_cache),
        "evictions": 0
    }
    logger.info("Cache statistics reset")








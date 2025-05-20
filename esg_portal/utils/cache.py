"""
Caching utilities for the ESG Portal
"""
import time
from functools import wraps
from flask import current_app

# Simple in-memory cache
_cache = {}

def cache_result(ttl=300):
    """
    Cache the result of a function for a specified time-to-live (TTL) in seconds.
    
    Args:
        ttl (int): Time to live in seconds. Default is 300 (5 minutes).
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create a cache key from function name and arguments
            key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Check if result is in cache and not expired
            if key in _cache:
                result, timestamp = _cache[key]
                if time.time() - timestamp < ttl:
                    current_app.logger.debug(f"Cache hit for {key}")
                    return result
            
            # Call the function and cache the result
            result = func(*args, **kwargs)
            _cache[key] = (result, time.time())
            current_app.logger.debug(f"Cache miss for {key}, storing result")
            
            return result
        return wrapper
    return decorator

def clear_cache():
    """Clear the entire cache"""
    global _cache
    _cache = {}
    current_app.logger.debug("Cache cleared")

def clear_cache_for_prefix(prefix):
    """
    Clear cache entries that start with a specific prefix
    
    Args:
        prefix (str): The prefix to match against cache keys
    """
    global _cache
    keys_to_remove = [k for k in _cache.keys() if k.startswith(prefix)]
    for key in keys_to_remove:
        del _cache[key]
    current_app.logger.debug(f"Cleared {len(keys_to_remove)} cache entries with prefix {prefix}") 
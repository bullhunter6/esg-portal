"""
Utilities for efficient caching of API responses and heavy computations.
"""
import hashlib
import json
import logging
import inspect
from functools import wraps
from datetime import datetime, timedelta
from flask import request, current_app
from esg_portal import cache

logger = logging.getLogger(__name__)

def generate_cache_key(prefix, *args, **kwargs):
    """
    Generate a unique cache key based on function arguments
    """
    # Convert args and kwargs to a string representation
    key_parts = [prefix]
    
    if args:
        for arg in args:
            # Handle non-hashable types like lists or dicts
            if isinstance(arg, (list, dict, set)):
                key_parts.append(hashlib.md5(json.dumps(arg, sort_keys=True).encode()).hexdigest())
            else:
                key_parts.append(str(arg))
    
    if kwargs:
        # Sort kwargs to ensure consistent order
        sorted_kwargs = sorted(kwargs.items())
        for k, v in sorted_kwargs:
            if isinstance(v, (list, dict, set)):
                key_parts.append(f"{k}:{hashlib.md5(json.dumps(v, sort_keys=True).encode()).hexdigest()}")
            else:
                key_parts.append(f"{k}:{v}")
    
    return "_".join(key_parts)

def cached_api_response(timeout=300):
    """
    Decorator for caching API responses
    
    Args:
        timeout: Cache timeout in seconds (default: 5 minutes)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key based on function name and arguments
            cache_key = generate_cache_key(
                f"api_{func.__module__}_{func.__name__}",
                *args,
                **kwargs
            )
            
            # Try to get from cache first
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.info(f"Cache hit for key: {cache_key}")
                return cached_result
            
            # Execute the function and cache the result
            logger.info(f"Cache miss for key: {cache_key}")
            result = func(*args, **kwargs)
            cache.set(cache_key, result, timeout=timeout)
            
            return result
        return wrapper
    return decorator

def invalidate_cache_pattern(pattern):
    """
    Invalidate all cache keys matching a pattern
    """
    if hasattr(cache, 'delete_pattern'):
        # Some cache backends support pattern deletion
        cache.delete_pattern(pattern)
    else:
        logger.warning("Cache backend does not support pattern deletion")

def clear_cache_for_function(func_name, module_name=None):
    """
    Clear all cached results for a specific function
    """
    if module_name is None and isinstance(func_name, str):
        pattern = f"api_*_{func_name}"
    elif module_name and isinstance(func_name, str):
        pattern = f"api_{module_name}_{func_name}"
    else:
        # Handle case where func_name is a function object
        function = func_name
        pattern = f"api_{function.__module__}_{function.__name__}"
    
    invalidate_cache_pattern(pattern)
    logger.info(f"Cleared cache for pattern: {pattern}")

def cache_function_result(function=None, timeout=300, key_prefix=None):
    """
    Decorator for caching function results
    
    Can be used as @cache_function_result or with parameters @cache_function_result(timeout=600)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get source code of the function for versioning
            source = inspect.getsource(func)
            source_hash = hashlib.md5(source.encode()).hexdigest()[:8]
            
            # Generate a prefix if not provided
            prefix = key_prefix or f"func_{func.__module__}_{func.__name__}_{source_hash}"
            
            # Generate cache key
            cache_key = generate_cache_key(prefix, *args, **kwargs)
            
            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, timeout=timeout)
            
            return result
        return wrapper
    
    # Handle both @cache_function_result and @cache_function_result(timeout=300)
    if function is None:
        return decorator
    else:
        return decorator(function) 
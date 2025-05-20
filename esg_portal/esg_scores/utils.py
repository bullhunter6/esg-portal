"""
Utility functions for ESG scores
"""
import time
import functools
from flask import current_app
from datetime import datetime, timedelta
import json

# In-memory cache for ESG scores
_esg_cache = {}
CACHE_TTL = 3600  # 1 hour cache TTL

def cache_esg_result(ttl=CACHE_TTL):
    """
    Cache decorator for ESG score results
    
    Args:
        ttl (int): Time to live in seconds (default: 1 hour)
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create a cache key from the function name and arguments
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Check if result is in cache and not expired
            if cache_key in _esg_cache:
                result, timestamp = _esg_cache[cache_key]
                if time.time() - timestamp < ttl:
                    try:
                        current_app.logger.debug(f"Cache hit for {cache_key}")
                    except RuntimeError:
                        # Outside of application context, just continue
                        print(f"Cache hit for {cache_key}")
                    return result
            
            # Call the function and cache the result
            result = func(*args, **kwargs)
            _esg_cache[cache_key] = (result, time.time())
            try:
                current_app.logger.debug(f"Cache miss for {cache_key}, caching result")
            except RuntimeError:
                # Outside of application context, just continue
                print(f"Cache miss for {cache_key}, caching result")
            
            # Clean up expired cache entries
            clean_expired_cache(ttl)
            
            return result
        return wrapper
    return decorator

def clean_expired_cache(ttl):
    """
    Clean up expired cache entries
    
    Args:
        ttl (int): Time to live in seconds
    """
    current_time = time.time()
    expired_keys = [key for key, (_, timestamp) in _esg_cache.items() 
                   if current_time - timestamp > ttl]
    
    for key in expired_keys:
        del _esg_cache[key]
    
    if expired_keys:
        try:
            current_app.logger.debug(f"Cleaned {len(expired_keys)} expired cache entries")
        except RuntimeError:
            # Outside of application context, just continue
            print(f"Cleaned {len(expired_keys)} expired cache entries")

def clear_cache():
    """Clear the entire ESG cache"""
    global _esg_cache
    _esg_cache = {}
    try:
        current_app.logger.info("ESG cache cleared")
    except RuntimeError:
        # Outside of application context, just continue
        print("ESG cache cleared")

def get_cache_stats():
    """Get cache statistics"""
    stats = {
        "total_entries": len(_esg_cache),
        "memory_usage_estimate": sum(len(str(result)) for result, _ in _esg_cache.values())
    }
    try:
        current_app.logger.debug(f"Cache stats: {stats}")
    except RuntimeError:
        # Outside of application context, just continue
        print(f"Cache stats: {stats}")
    return stats

def format_esg_score(score, source):
    """
    Format an ESG score for display
    
    Args:
        score (str): The score to format
        source (str): The source of the score
        
    Returns:
        tuple: (formatted_score, css_class)
    """
    # Debug logging
    print(f"Formatting score for {source}: {score}")
    
    if score == '-' or score == 'N/A':
        print(f"No score for {source}, returning no-score")
        return score, 'no-score'
    
    # Format based on source
    if source == 'S&P':
        try:
            score_val = float(score)
            print(f"S&P score value: {score_val}")
            if score_val >= 70:
                return score, 'high-score'
            elif score_val >= 50:
                return score, 'medium-score'
            else:
                return score, 'low-score'
        except (ValueError, TypeError) as e:
            print(f"Error processing S&P score: {e}")
            return score, 'no-score'
    
    elif source == 'Sustainalytics':
        try:
            score_val = float(score)
            print(f"Sustainalytics score value: {score_val}")
            if score_val <= 10:
                return score, 'high-score'
            elif score_val <= 30:
                return score, 'medium-score'
            else:
                return score, 'low-score'
        except (ValueError, TypeError) as e:
            print(f"Error processing Sustainalytics score: {e}")
            return score, 'no-score'
    
    elif source == 'LSEG':
        try:
            score_val = float(score)
            print(f"LSEG score value: {score_val}")
            if score_val >= 75:
                return score, 'high-score'
            elif score_val >= 50:
                return score, 'medium-score'
            else:
                return score, 'low-score'
        except (ValueError, TypeError) as e:
            print(f"Error processing LSEG score: {e}")
            return score, 'no-score'
    
    elif source == 'MSCI':
        print(f"MSCI score: {score}")
        if score in ['AAA', 'AA']:
            return score, 'high-score'
        elif score in ['A', 'BBB']:
            return score, 'medium-score'
        elif score in ['BB', 'B', 'CCC']:
            return score, 'low-score'
        else:
            return score, 'no-score'
    
    elif source == 'ISS':
        print(f"ISS score: {score}")
        if score in ['A+', 'A', 'A-']:
            return score, 'high-score'
        elif score in ['B+', 'B', 'B-']:
            return score, 'medium-score'
        elif score in ['C+', 'C', 'C-', 'D+', 'D', 'D-']:
            return score, 'low-score'
        else:
            return score, 'no-score'
    
    # Default case
    print(f"Unhandled source {source}, returning no-score")
    return score, 'no-score'

def generate_esg_table(scores_data):
    """
    Generate an HTML table from ESG scores data
    
    Args:
        scores_data (dict): Dictionary containing ESG scores
        
    Returns:
        dict: Dictionary with table_headers and table_rows
    """
    # Define the table headers
    headers = ["Source", "Score", "Rating", "Date", "Details"]
    
    # Initialize rows
    rows = []
    
    # Generate rows for each source
    sources = ["S&P", "Sustainalytics", "ISS", "LSEG", "MSCI"]
    
    for source in sources:
        if source in scores_data:
            source_data = scores_data[source]
            
            # Format the score
            score = source_data.get("score", "-")
            formatted_score, css_class = format_esg_score(score, source)
            
            # Get rating if available
            rating = source_data.get("rating", "-")
            
            # Get date if available (or use N/A)
            date_value = source_data.get("date", "-")
            if date_value and date_value != "-":
                try:
                    # Try to parse and format the date
                    if isinstance(date_value, str):
                        date_obj = datetime.strptime(date_value, "%Y-%m-%d")
                        date = date_obj.strftime("%b %d, %Y")
                    elif isinstance(date_value, datetime):
                        date = date_value.strftime("%b %d, %Y")
                    else:
                        date = date_value
                except (ValueError, TypeError):
                    date = date_value
            else:
                date = "-"
            
            # Get details link if available
            details_url = source_data.get("details_url", "#")
            has_details = details_url and details_url != "#"
            
            # Add row
            rows.append({
                "source": source,
                "score": formatted_score,
                "score_class": css_class,
                "rating": rating,
                "date": date,
                "details_url": details_url,
                "has_details": has_details
            })
        else:
            # Add empty row for missing source
            rows.append({
                "source": source,
                "score": "-",
                "score_class": "no-score",
                "rating": "-",
                "date": "-",
                "details_url": "#",
                "has_details": False
            })
    
    return {
        "table_headers": headers,
        "table_rows": rows
    }
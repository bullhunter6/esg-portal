"""
Database utilities for optimizing connection management.
"""
import time
import logging
from functools import wraps
from sqlalchemy.exc import SQLAlchemyError
from flask import current_app
from esg_portal import db

logger = logging.getLogger(__name__)

def with_db_retry(max_retries=3, retry_delay=0.5):
    """
    Decorator to retry database operations with exponential backoff
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            last_error = None
            
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except SQLAlchemyError as e:
                    last_error = e
                    retries += 1
                    
                    if retries >= max_retries:
                        logger.error(f"Database operation failed after {max_retries} retries: {str(e)}")
                        break
                    
                    # Exponential backoff
                    wait_time = retry_delay * (2 ** (retries - 1))
                    logger.warning(f"Database operation failed, retrying in {wait_time}s: {str(e)}")
                    time.sleep(wait_time)
                    
                    # Ensure we have a fresh connection
                    db.session.rollback()
            
            # If we get here, all retries failed
            raise last_error
        
        return wrapper
    return decorator

def optimize_query(query, chunk_size=1000):
    """
    Generator to optimize large queries by breaking them into chunks
    """
    offset = 0
    while True:
        chunk = query.limit(chunk_size).offset(offset).all()
        if not chunk:
            break
        
        for item in chunk:
            yield item
        
        offset += chunk_size
        # Ensure previous results are garbage collected
        db.session.expire_all()

def check_db_connection():
    """
    Test database connection and report status
    """
    try:
        # Simple test query
        result = db.session.execute("SELECT 1").scalar()
        if result == 1:
            return True, "Database connection successful"
        else:
            return False, "Unexpected result from database test"
    except Exception as e:
        return False, f"Database connection failed: {str(e)}"

def get_connection_pool_status():
    """
    Get current status of the SQLAlchemy connection pool
    """
    engine = db.engine
    if hasattr(engine, 'pool'):
        status = {
            'size': engine.pool.size() if hasattr(engine.pool, 'size') else 'Unknown',
            'checkedin': engine.pool.checkedin() if hasattr(engine.pool, 'checkedin') else 'Unknown',
            'overflow': engine.pool.overflow() if hasattr(engine.pool, 'overflow') else 'Unknown',
            'checkedout': engine.pool.checkedout() if hasattr(engine.pool, 'checkedout') else 'Unknown',
        }
        return status
    return {'status': 'No pool information available'} 
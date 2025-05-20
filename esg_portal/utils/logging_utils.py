"""
Logging utilities for ESG Portal
"""
import os
import json
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from flask import request, g, has_request_context

# Create loggers
user_logger = logging.getLogger('user_activity')
error_logger = logging.getLogger('error_log')

def setup_logging(app):
    """
    Set up logging for the application
    
    Args:
        app: Flask application instance
    """
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(app.instance_path, 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    # Configure rotating file handler for application logs
    app_log_file = os.path.join(logs_dir, 'app.log')
    file_handler = RotatingFileHandler(app_log_file, maxBytes=1024*1024*10, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    
    # Configure error log file
    error_log_file = os.path.join(logs_dir, 'errors.log')
    error_file_handler = RotatingFileHandler(error_log_file, maxBytes=1024*1024*10, backupCount=10)
    error_file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    error_file_handler.setLevel(logging.ERROR)
    
    # Set up user activity log file
    app.config['USER_ACTIVITY_LOG'] = os.path.join(logs_dir, 'user_activity.json')
    
    # Add handlers to application logger
    app.logger.addHandler(file_handler)
    app.logger.addHandler(error_file_handler)
    app.logger.setLevel(logging.INFO)
    
    # Log that logging has been set up
    app.logger.info(f'Logging initialized. User logs: {app.config["USER_ACTIVITY_LOG"]}, Error logs: {error_log_file}')

def log_user_activity(user_id, action, status=None, details=None):
    """
    Log user activity to a JSON file
    
    Args:
        user_id: ID of the user performing the action
        action: Type of action performed
        status: Status of the action (e.g., success, failure)
        details: Dictionary with additional details
    """
    from flask import current_app
    
    # Skip if logging is disabled
    if not current_app.config.get('LOGGING_ENABLED', True):
        return
    
    # Create log entry
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'user_id': user_id,
        'action': action,
        'details': details or {},
    }
    
    # Add status if provided
    if status:
        log_entry['status'] = status
    
    # Add request information if available
    if has_request_context():
        log_entry['ip'] = request.remote_addr
        log_entry['user_agent'] = request.user_agent.string
        log_entry['path'] = request.path
    
    # Get the log file path
    log_file = current_app.config.get('USER_ACTIVITY_LOG')
    if not log_file:
        current_app.logger.warning('User activity log file not configured')
        return
    
    # Ensure log directory exists
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    # Append to log file
    try:
        with open(log_file, 'a+', encoding='utf-8') as f:
            json.dump(log_entry, f)
            f.write('\n')
    except Exception as e:
        current_app.logger.error(f'Failed to log user activity: {e}')

def log_error(exception, user_id=None, additional_info=None):
    """
    Log an error with user information
    
    Args:
        exception: The exception to log
        user_id: ID of the user (if available)
        additional_info: Dictionary with additional context
    """
    from flask import current_app
    
    # Create error details
    error_details = {
        'error': str(exception),
        'type': type(exception).__name__,
        'timestamp': datetime.now().isoformat(),
    }
    
    # Add user ID if available
    if user_id:
        error_details['user_id'] = user_id
    
    # Add request information if available
    if has_request_context():
        error_details['ip'] = request.remote_addr
        error_details['user_agent'] = request.user_agent.string
        error_details['path'] = request.path
        error_details['method'] = request.method
    
    # Add additional info
    if additional_info:
        error_details['additional_info'] = additional_info
    
    # Log the error
    current_app.logger.error(f"Error: {error_details['error']}", exc_info=True, extra=error_details) 
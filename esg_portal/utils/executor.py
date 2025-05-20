"""
Executor utility for handling background tasks
"""
from flask_executor import Executor
import uuid
import os
from datetime import datetime
import json

# Initialize executor
executor = Executor()

# Dictionary to store task information
task_tracker = {}

def init_app(app):
    """Initialize the executor with the Flask app"""
    executor.init_app(app)
    app.config.setdefault('EXECUTOR_TYPE', 'thread')
    app.config.setdefault('EXECUTOR_MAX_WORKERS', 10)
    
    # Create a directory for task status files if it doesn't exist
    task_status_dir = os.path.join(app.instance_path, 'task_status')
    os.makedirs(task_status_dir, exist_ok=True)
    app.config['TASK_STATUS_DIR'] = task_status_dir
    
    return executor

def generate_task_id():
    """Generate a unique task ID"""
    return str(uuid.uuid4())

def update_task_status(task_id, status_update):
    """Update the status of a task"""
    if task_id in task_tracker:
        task_tracker[task_id].update(status_update)
    else:
        task_tracker[task_id] = status_update
    
    # Also save to file for persistence across restarts
    task_status_dir = os.environ.get('TASK_STATUS_DIR')
    if task_status_dir:
        status_file = os.path.join(task_status_dir, f"{task_id}.json")
        with open(status_file, 'w') as f:
            json.dump(task_tracker[task_id], f)
    
    return task_tracker[task_id]

def get_task_status(task_id):
    """Get the current status of a task"""
    return task_tracker.get(task_id, {"status": "unknown"})

def cancel_task(task_id):
    """Mark a task as cancelled"""
    if task_id in task_tracker:
        task_tracker[task_id]['status'] = 'cancelled'
        return True
    return False

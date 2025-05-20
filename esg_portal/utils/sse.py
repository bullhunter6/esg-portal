"""
Server-Sent Events (SSE) utilities for real-time updates
"""
from flask import Response, stream_with_context
import json
import time

def sse_stream(task_id, task_tracker):
    """Generate SSE stream for task progress updates"""
    def generate():
        yield "data: {}\n\n".format(json.dumps({"status": "connected", "task_id": task_id}))
        
        while True:
            # Get current task status
            task_info = task_tracker.get(task_id)
            if not task_info:
                yield "data: {}\n\n".format(json.dumps({"status": "error", "message": "Task not found"}))
                break
                
            # Send current status
            yield "data: {}\n\n".format(json.dumps(task_info))
            
            # If task is complete or errored, end the stream
            if task_info.get('status') in ['complete', 'error', 'cancelled']:
                break
                
            time.sleep(1)  # Check every second
    
    return Response(stream_with_context(generate()), mimetype="text/event-stream")

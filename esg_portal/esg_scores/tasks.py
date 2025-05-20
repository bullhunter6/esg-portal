"""
Celery tasks for ESG score processing
"""
import os
from datetime import datetime
from celery import shared_task
from flask import current_app
import logging

from esg_portal.esg_scores.excel_updater import parse_excel_for_companies, update_excel_file, process_company
from esg_portal import socketio

logger = logging.getLogger(__name__)

# Use shared_task instead of celery.task to avoid circular imports
@shared_task(bind=True, name='esg_portal.esg_scores.tasks.process_excel_file')
def process_excel_file(self, file_path, original_filename, user_id):
    """Process an Excel file in the background using Celery"""
    logger.info(f"Starting Excel file processing task: {self.request.id}")
    logger.info(f"File: {file_path}, User: {user_id}")
    
    try:
        # Update task state to indicate progress
        self.update_state(state='PROGRESS', meta={
            'status': 'processing',
            'progress': 0,
            'original_filename': original_filename,
            'start_time': datetime.now().isoformat()
        })
        
        logger.info(f"Task state updated to PROGRESS: {self.request.id}")
        
        # Emit processing started event
        try:
            if socketio:
                socketio.emit('task_update', {
                    'task_id': self.request.id,
                    'user_id': str(user_id),
                    'status': 'processing',
                    'message': f'Processing file {original_filename}',
                    'progress': 0,
                    'timestamp': datetime.now().isoformat()
                }, namespace='/tasks')
                logger.info(f"SocketIO event emitted for processing start: {self.request.id}")
            else:
                logger.warning("SocketIO not available, skipping emit")
        except Exception as e:
            logger.error(f"Error emitting SocketIO event: {e}")
        
        # Validate file path
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return {
                'status': 'error',
                'message': f'File not found: {file_path}',
                'user_id': user_id
            }
        
        # Parse the Excel file for companies
        logger.info(f"Parsing Excel file: {file_path}")
        companies_data = parse_excel_for_companies(file_path)
        
        if not companies_data:
            logger.warning(f"No companies found in Excel file: {file_path}")
            return {
                'status': 'error',
                'message': 'No companies found in the Excel file',
                'user_id': user_id
            }
        
        logger.info(f"Found {len(companies_data)} companies in Excel file")
        
        # Process companies and collect their scores
        processed_companies = {}
        total_companies = len(companies_data)
        
        for i, company_data in enumerate(companies_data):
            # Update progress
            progress = int((i / total_companies) * 100)
            self.update_state(state='PROGRESS', meta={
                'status': 'processing',
                'progress': progress,
                'current': i + 1,
                'total': total_companies,
                'original_filename': original_filename,
                'start_time': datetime.now().isoformat()
            })
            
            # Process the company
            company_name = company_data["name"]
            logger.info(f"Processing company {i+1}/{total_companies}: {company_name}")
            result = process_company(company_data)
            processed_companies[company_name] = result["scores"]
            
            # Emit progress update every 5 companies or for the last company
            if i % 5 == 0 or i == total_companies - 1:
                try:
                    if socketio:
                        socketio.emit('task_update', {
                            'task_id': self.request.id,
                            'user_id': str(user_id),
                            'status': 'processing',
                            'progress': progress,
                            'current': i + 1,
                            'total': total_companies,
                            'timestamp': datetime.now().isoformat()
                        }, namespace='/tasks')
                        logger.info(f"SocketIO progress update emitted: {progress}%")
                    else:
                        logger.warning("SocketIO not available, skipping emit")
                except Exception as e:
                    logger.error(f"Error emitting SocketIO event: {e}")
        
        # Generate output filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(current_app.config['UPLOAD_FOLDER'], f"updated_esg_scores_{timestamp}.xlsx")
        
        # Update the Excel file with ESG scores
        logger.info(f"Updating Excel file with ESG scores: {output_file}")
        download_filename = update_excel_file(file_path, companies_data, output_file)
        
        # Generate summary data for display
        summary_headers = ["Company Name", "S&P", "Sustainalytics", "ISS", "LSEG", "MSCI"]
        
        summary_rows = []
        for company_name, scores in processed_companies.items():
            row = [company_name]
            for source in ["S&P", "Sustainalytics", "ISS", "LSEG", "MSCI"]:
                row.append(scores.get(source, "-"))
            summary_rows.append(row)
        
        # Extract just the filename from the full path
        download_filename = os.path.basename(download_filename) if isinstance(download_filename, str) else download_filename
        
        completed_at = datetime.now().isoformat()
        logger.info(f"Excel processing complete: {download_filename}")
        
        # Emit completion event
        try:
            if socketio:
                socketio.emit('task_update', {
                    'task_id': self.request.id,
                    'user_id': str(user_id),
                    'status': 'complete',
                    'download_filename': download_filename,
                    'completed_at': completed_at,
                    'timestamp': datetime.now().isoformat(),
                    'progress': 100
                }, namespace='/tasks')
                logger.info(f"SocketIO completion event emitted for task: {self.request.id}")
            else:
                logger.warning("SocketIO not available, skipping emit")
        except Exception as e:
            logger.error(f"Error emitting SocketIO event: {e}")
        
        # Return the final result
        return {
            'status': 'complete',
            'user_id': user_id,
            'download_filename': download_filename,
            'summary_headers': summary_headers,
            'summary_rows': summary_rows,
            'original_filename': original_filename,
            'completed_at': completed_at
        }
        
    except Exception as e:
        logger.error(f"Error in Celery task: {e}", exc_info=True)
        
        # Emit error event
        try:
            if socketio:
                socketio.emit('task_update', {
                    'task_id': self.request.id,
                    'user_id': str(user_id),
                    'status': 'error',
                    'message': str(e),
                    'timestamp': datetime.now().isoformat()
                }, namespace='/tasks')
                logger.info(f"SocketIO error event emitted for task: {self.request.id}")
            else:
                logger.warning("SocketIO not available, skipping emit")
        except Exception as socket_err:
            logger.error(f"Error emitting SocketIO event: {socket_err}")
        
        # Return error status
        return {
            'status': 'error',
            'message': f'Error updating Excel file: {str(e)}',
            'user_id': user_id
        } 
"""
Routes for the ESG scores module
"""
import os
import uuid
import threading
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, current_app, send_from_directory, send_file, session, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from celery.result import AsyncResult 
import logging

from esg_portal.esg_scores import bp
from esg_portal.esg_scores.search import fetch_score, fetch_all_scores
from esg_portal.esg_scores.excel_updater import update_excel_file, parse_excel_for_companies, process_company
# Import celery instead of the task directly to avoid circular imports
from esg_portal.esg_scores.forms import UploadForm, SearchForm
from esg_portal.utils.logging_utils import log_user_activity, log_error
from esg_portal.esg_scores.utils import format_esg_score, generate_esg_table

# Dictionary to store task IDs for each user
user_tasks = {}

def allowed_file(filename):
    """Check if a file has an allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ['xlsx', 'xls']

def ensure_upload_folder():
    """Ensure the upload folder exists and return its path"""
    upload_folder = current_app.config.get('UPLOAD_FOLDER')
    if not upload_folder:
        current_app.config['UPLOAD_FOLDER'] = os.path.join(current_app.instance_path, 'uploads')
        upload_folder = current_app.config['UPLOAD_FOLDER']
    
    # Ensure the directory exists
    os.makedirs(upload_folder, exist_ok=True)
    
    current_app.logger.info(f"Upload folder created at: {upload_folder}")
    
    return upload_folder

def process_excel_in_background(file_path, user_id, app):
    """Process an Excel file in the background"""
    with app.app_context():
        try:
            # Get the current task info
            task_info = background_tasks.get(user_id, {}).copy()
            
            # Parse the Excel file for companies
            companies_data = parse_excel_for_companies(file_path)
            
            if not companies_data:
                task_info.update({
                    'status': 'error',
                    'message': 'No companies found in the Excel file'
                })
                background_tasks[user_id] = task_info
                return
            
            # Check if processing was cancelled
            if user_id in background_tasks and background_tasks[user_id].get('status') == 'cancelled':
                return
            
            # Process companies and collect their scores
            processed_companies = {}
            for company_data in companies_data:
                company_name = company_data["name"]
                # Process the company to get scores
                result = process_company(company_data)
                processed_companies[company_name] = result["scores"]
            
            # Check if processing was cancelled
            if user_id in background_tasks and background_tasks[user_id].get('status') == 'cancelled':
                return
            
            # Generate output filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = os.path.join(app.config['UPLOAD_FOLDER'], f"updated_esg_scores_{timestamp}.xlsx")
            
            # Update the Excel file with ESG scores
            download_filename = update_excel_file(file_path, companies_data, output_file)
            
            # Check if processing was cancelled
            if user_id in background_tasks and background_tasks[user_id].get('status') == 'cancelled':
                return
            
            # Generate summary data for display
            summary_headers = ["Company Name", "S&P", "Sustainalytics", "ISS", "LSEG", "MSCI"]
            
            summary_rows = []
            for company_name, scores in processed_companies.items():
                row = [company_name]
                for source in ["S&P", "Sustainalytics", "ISS", "LSEG", "MSCI"]:
                    row.append(scores.get(source, "-"))
                summary_rows.append(row)
            
            # Check if processing was cancelled
            if user_id in background_tasks and background_tasks[user_id].get('status') == 'cancelled':
                return
            
            # Extract just the filename from the full path
            download_filename = os.path.basename(download_filename) if isinstance(download_filename, str) else download_filename
            
            # Update task info with results
            task_info.update({
                'status': 'complete',
                'download_filename': download_filename,
                'summary_headers': summary_headers,
                'summary_rows': summary_rows,
                'completed_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            
            # Store the result in the background_tasks dictionary
            background_tasks[user_id] = task_info
            
        except Exception as e:
            app.logger.error(f"Error updating Excel file: {e}")
            
            # Get current task info
            task_info = background_tasks.get(user_id, {}).copy()
            
            # Update with error status
            task_info.update({
                'status': 'error',
                'message': f'Error updating Excel file: {str(e)}'
            })
            
            background_tasks[user_id] = task_info

@bp.route('/')
def index():
    """ESG scores home page"""
    return render_template('esg_scores/index.html')

@bp.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    """Search for ESG scores"""
    tab = request.args.get('tab', 'All')
    company_name = request.args.get('company_name') or request.form.get('company_name')
    year = request.args.get('year') or request.form.get('year')
    scores = {}
    details = {}
    
    if company_name:
        try:
            # Log the search activity
            user_id = current_user.id if current_user.is_authenticated else 'anonymous'
            log_data = {
                "company_name": company_name,
                "tab": tab
            }
            if year:
                log_data["year"] = year
                
            log_user_activity(
                user_id=user_id,
                action="esg_score_search",
                details=log_data
            )
            
            # Check cache first before making API calls
            cache_key = f"esg_scores_{company_name}_{tab}_{year if year else 'current'}"
            cached_result = cache.get(cache_key)
            
            if cached_result:
                current_app.logger.info(f"Using cached ESG scores for {company_name}")
                if tab == 'All':
                    scores = cached_result
                else:
                    details = cached_result
            else:
                if tab == 'All':
                    scores = fetch_all_scores(company_name)
                    # Format scores for display
                    formatted_scores = {}
                    for source, score in scores.items():
                        formatted_score, css_class = format_esg_score(score, source)
                        formatted_scores[source] = {
                            'value': formatted_score,
                            'class': css_class
                        }
                    scores = formatted_scores
                    # Cache the result for 5 minutes
                    cache.set(cache_key, scores, timeout=300)
                else:
                    details = fetch_score(tab, company_name, year)
                    # Cache the result for 5 minutes
                    cache.set(cache_key, details, timeout=300)
        except Exception as e:
            log_error(e, user_id=user_id if current_user.is_authenticated else None,
                     additional_info={"company_name": company_name, "tab": tab, "year": year})
            flash(f"Error searching for ESG scores: {str(e)}", 'danger')
    
    return render_template(
        'esg_scores/search.html',
        tab=tab,
        company_name=company_name,
        scores=scores,
        details=details
    )

@bp.route('/excel_updater', methods=['GET', 'POST'])
@login_required
def excel_updater():
    """Excel updater page with real-time progress updates."""
    form = UploadForm()
    
    # Ensure the upload folder exists
    upload_folder = ensure_upload_folder()
    
    # Debug logging
    current_app.logger.info(f"Excel updater accessed by user {current_user.username}")
    
    # Check for clear parameter
    if request.args.get('clear'):
        # Clear user tasks
        user_id = str(current_user.id)
        if user_id in user_tasks:
            user_tasks[user_id] = {}
        current_app.logger.info(f"Cleared tasks for user {current_user.username}")
        return redirect(url_for('esg_scores.excel_updater'))
    
    # Initialize variables
    task_id = None
    task_status = 'ready'
    uploaded_file = None
    download_filename = None
    summary_headers = None
    summary_rows = None
    
    # Get the most recent task for this user
    user_id = str(current_user.id)
    if user_id in user_tasks and user_tasks[user_id]:
        # Get the most recent task
        task_id = list(user_tasks[user_id].keys())[-1]
        task_info = user_tasks[user_id][task_id]
        task_status = task_info.get('status', 'ready')
        uploaded_file = task_info.get('original_filename')
        
        # Debug logging
        current_app.logger.info(f"Found existing task for user {current_user.username}: {task_id} - Status: {task_status}")
        
        # If task is complete, get results
        if task_status == 'complete':
            download_filename = task_info.get('download_filename')
            summary_headers = task_info.get('summary_headers')
            summary_rows = task_info.get('summary_rows')
    else:
        task_info = {
            'status': 'ready',
            'progress': 0,
            'original_filename': None,
            'start_time': None
        }
    
    if form.validate_on_submit():
        try:
            # Get the uploaded file
            f = form.file.data
            original_filename = f.filename
            
            current_app.logger.info(f"File uploaded by user {current_user.username}: {original_filename}")
            
            # Create a unique ID for this upload
            upload_id = str(uuid.uuid4())
            
            # Save to a temporary location with a unique name
            temp_filename = f"temp_{upload_id}.xlsx"
            filepath = os.path.join(upload_folder, temp_filename)
            
            current_app.logger.info(f"Saving file to {filepath}")
            
            # Ensure the directory exists again right before saving
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Save the file
            try:
                f.save(filepath)
                current_app.logger.info(f"File saved successfully to {filepath}")
                
                # Verify file exists
                if not os.path.exists(filepath):
                    raise FileNotFoundError(f"File was not saved properly: {filepath}")
                
                file_size = os.path.getsize(filepath)
                current_app.logger.info(f"File size: {file_size} bytes")
            except Exception as save_error:
                current_app.logger.error(f"Error saving file: {save_error}")
                flash(f"Error saving file: {str(save_error)}", 'danger')
                return render_template(
                    'esg_scores/excel_updater.html', 
                    title='Excel Updater',
                    form=form,
                    task_id=None,
                    task_info=task_info,
                    task_status='ready',
                    uploaded_file=None
                )
            
            # Import the task function here to avoid circular imports
            from esg_portal.esg_scores.tasks import process_excel_file
            
            # Start the celery task
            current_app.logger.info(f"Starting Celery task for file {filepath}")
            
            task = process_excel_file.delay(filepath, original_filename, current_user.id)
            task_id = task.id
            
            current_app.logger.info(f"Celery task created with ID: {task_id}")
            
            # Store task info for this user
            user_id = str(current_user.id)
            if user_id not in user_tasks:
                user_tasks[user_id] = {}
            
            user_tasks[user_id][task_id] = {
                'status': 'processing',
                'progress': 0,
                'original_filename': original_filename,
                'filepath': filepath,
                'start_time': datetime.now().isoformat()
            }
            
            current_app.logger.info(f"Task info stored for user {user_id}: {task_id}")
            
            # Update variables for template
            task_status = 'processing'
            uploaded_file = original_filename
            task_info = user_tasks[user_id][task_id]
            
            # Emit event to notify about new task
            try:
                socketio.emit('task_update', {
                    'task_id': task_id,
                    'status': 'started',
                    'message': f'Processing file {original_filename}',
                    'progress': 0,
                    'user_id': user_id,
                    'timestamp': datetime.now().isoformat()
                }, namespace='/tasks')
                
                current_app.logger.info(f"SocketIO event emitted for task {task_id}")
            except Exception as e:
                current_app.logger.error(f"Error emitting SocketIO event: {e}")
            
            flash(f'File "{original_filename}" is being processed. Please wait...', 'info')
            
            # Log the activity
            log_user_activity(
                user_id=current_user.id,
                action="excel_file_upload",
                status="processing",
                details={"filename": original_filename, "task_id": task_id}
            )
            
            current_app.logger.info(f"User {current_user.username} uploaded file {original_filename} for processing. Task ID: {task_id}")
            
            # Redirect to the same page to prevent form resubmission
            return redirect(url_for('esg_scores.excel_updater'))
            
        except Exception as e:
            error_msg = f"Error processing file: {str(e)}"
            flash(error_msg, 'danger')
            current_app.logger.error(f"Error processing file for user {current_user.username}: {str(e)}", exc_info=True)
    
    return render_template(
        'esg_scores/excel_updater.html', 
        title='Excel Updater',
        form=form,
        task_id=task_id,
        task_info=task_info,
        task_status=task_status,
        uploaded_file=uploaded_file,
        download_filename=download_filename,
        summary_headers=summary_headers,
        summary_rows=summary_rows
    )

@bp.route('/check_task_status/<task_id>')
@login_required
def check_task_status(task_id):
    """Check the status of a task and return JSON with progress."""
    user_id = str(current_user.id)
    
    # First, check Celery task status
    try:
        task_result = AsyncResult(task_id, app=celery)
        task_state = task_result.state
        
        # Get task info from user_tasks dictionary
        task_info = user_tasks.get(user_id, {}).get(task_id, {})
        
        if task_state == 'PENDING':
            response = {
                'status': 'pending',
                'message': 'Task is pending...',
                'progress': 0
            }
        elif task_state == 'FAILURE':
            response = {
                'status': 'error',
                'message': str(task_result.result),
                'progress': 0
            }
        elif task_state == 'SUCCESS':
            result = task_result.result
            response = {
                'status': 'complete',
                'message': 'Task completed successfully',
                'progress': 100,
                'download_filename': result.get('download_filename'),
                'summary_headers': result.get('summary_headers'),
                'summary_rows': result.get('summary_rows')
            }
        else:  # 'STARTED', 'PROGRESS', etc.
            info = task_result.info
            if isinstance(info, dict):
                # Get progress info from the task
                progress = info.get('progress', 0)
                message = info.get('message', 'Processing...')
                current = info.get('current', 0)
                total = info.get('total', 0)
                
                response = {
                    'status': 'processing',
                    'message': message,
                    'progress': progress,
                    'current': current,
                    'total': total
                }
            else:
                response = {
                    'status': 'processing',
                    'message': 'Task is running...',
                    'progress': task_info.get('progress', 0)
                }
    except Exception as e:
        current_app.logger.error(f"Error checking task status: {e}")
        response = {
            'status': 'error',
            'message': f'Error checking task status: {str(e)}',
            'progress': 0
        }
    
    return jsonify(response)

@bp.route('/download/<filename>')
@login_required
def download_file(filename):
    """Download a file from the upload folder"""
    try:
        # Ensure the file exists
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(file_path):
            flash(f"File not found: {filename}", 'danger')
            return redirect(url_for('esg_scores.excel_updater'))
        
        # Log file download
        log_user_activity(
            user_id=current_user.id,
            action="excel_file_download",
            details={"filename": filename}
        )
        
        current_app.logger.info(f"User {current_user.username} is downloading file {filename}")
        
        # Send the file
        return send_from_directory(
            current_app.config['UPLOAD_FOLDER'],
            filename,
            as_attachment=True
        )
    except Exception as e:
        log_error(e, user_id=current_user.id,
                 additional_info={"filename": filename})
        current_app.logger.error(f"Error downloading file {filename}: {str(e)}")
        flash(f"Error downloading file: {str(e)}", 'danger')
        return redirect(url_for('esg_scores.excel_updater'))

@bp.route('/cancel-processing')
@login_required
def cancel_processing():
    """Cancel the current processing task"""
    user_id = str(current_user.id)
    task_id = user_tasks.get(user_id)
    
    if task_id:
        # Revoke the Celery task
        celery.control.revoke(task_id, terminate=True)
        
        # Remove the task ID from the user_tasks dictionary
        user_tasks.pop(user_id, None)
        
        flash('Processing has been cancelled', 'info')
    
    return redirect(url_for('esg_scores.excel_updater')) 
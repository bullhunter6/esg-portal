"""
Simplified routes for the ESG scores module using SSE and Flask-Executor
"""
import os
import uuid
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, current_app, send_from_directory, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import logging

from esg_portal.esg_scores import bp
from esg_portal.esg_scores.search import fetch_score, fetch_all_scores, stream_all_scores
from esg_portal.esg_scores.excel_updater import update_excel_file, parse_excel_for_companies, process_company
from esg_portal.utils.executor import executor, task_tracker, generate_task_id, update_task_status, get_task_status, cancel_task
from esg_portal.utils.sse import sse_stream
from esg_portal import cache, db
from esg_portal.esg_scores.forms import UploadForm, SearchForm
from esg_portal.utils.logging_utils import log_user_activity, log_error
from esg_portal.esg_scores.utils import format_esg_score, generate_esg_table
from esg_portal.models.file_upload import FileUpload
import re
import pandas as pd

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

def process_excel_file(file_path, task_id, user_id):
    """Process an Excel file in the background"""
    try:
        # Update task status to processing
        update_task_status(task_id, {
            'status': 'processing',
            'progress': 0,
            'message': 'Starting to process Excel file'
        })
        
        # Parse the Excel file for companies
        companies_data = parse_excel_for_companies(file_path)
        
        if not companies_data:
            update_task_status(task_id, {
                'status': 'error',
                'message': 'No companies found in the Excel file'
            })
            
            # Update database record
            file_upload = FileUpload.query.filter_by(task_id=task_id).first()
            if file_upload:
                file_upload.status = 'error'
                file_upload.error_message = 'No companies found in the Excel file'
                db.session.commit()
                
            return
        
        total_companies = len(companies_data)
        update_task_status(task_id, {
            'status': 'processing',
            'progress': 5,
            'message': f'Found {total_companies} companies in the Excel file',
            'total_companies': total_companies,
            'processed_companies': 0
        })
        
        # Process companies and collect their scores
        processed_companies = {}
        for i, company_data in enumerate(companies_data):
            # Check if processing was cancelled
            if get_task_status(task_id).get('status') == 'cancelled':
                return
                
            company_name = company_data["name"]
            update_task_status(task_id, {
                'status': 'processing',
                'progress': 5 + (i * 85 // total_companies),
                'message': f'Processing company {i+1}/{total_companies}: {company_name}',
                'current_company': company_name,
                'processed_companies': i
            })
            
            # Process the company to get scores
            result = process_company(company_data)
            processed_companies[company_name] = result["scores"]
        
        # Check if processing was cancelled
        if get_task_status(task_id).get('status') == 'cancelled':
            return
        
        # Generate output filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(current_app.config['UPLOAD_FOLDER'], f"updated_esg_scores_{timestamp}.xlsx")
        
        update_task_status(task_id, {
            'status': 'processing',
            'progress': 90,
            'message': 'Generating Excel file with results',
            'processed_companies': total_companies
        })
        
        # Update the Excel file with ESG scores
        output_filename = update_excel_file(file_path, companies_data, output_file)
        
        # Check if processing was cancelled
        if get_task_status(task_id).get('status') == 'cancelled':
            return
        
        # Generate summary data for display
        summary_headers = ["Company Name", "S&P", "Sustainalytics", "ISS", "LSEG", "MSCI"]
        
        summary_rows = []
        for company_name, scores in processed_companies.items():
            row = [company_name]
            for source in ["S&P", "Sustainalytics", "ISS", "LSEG", "MSCI"]:
                row.append(scores.get(source, "-"))
            summary_rows.append(row)
        
        # Extract just the filename from the full path
        output_basename = os.path.basename(output_filename) if isinstance(output_filename, str) else output_filename
        
        # Update task status with results
        update_task_status(task_id, {
            'status': 'complete',
            'progress': 100,
            'message': 'Processing complete',
            'download_filename': output_basename,
            'summary_headers': summary_headers,
            'summary_rows': summary_rows,
            'completed_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        # Update database record
        file_upload = FileUpload.query.filter_by(task_id=task_id).first()
        if file_upload:
            file_upload.status = 'complete'
            file_upload.output_filename = output_basename
            db.session.commit()
        
    except Exception as e:
        current_app.logger.error(f"Error processing Excel file: {e}")
        
        # Update task status with error
        update_task_status(task_id, {
            'status': 'error',
            'message': f'Error processing Excel file: {str(e)}'
        })
        
        # Update database record
        file_upload = FileUpload.query.filter_by(task_id=task_id).first()
        if file_upload:
            file_upload.status = 'error'
            file_upload.error_message = str(e)
            db.session.commit()

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
                        print(f"Processing score for {source}: {score}")
                        formatted_score, css_class = format_esg_score(score, source)
                        print(f"Formatted score for {source}: {formatted_score}, CSS class: {css_class}")
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
        year=year,
        scores=scores,
        details=details
    )

@bp.route('/excel-updater', methods=['GET', 'POST'])
@login_required
def excel_updater():
    """Excel updater page with real-time progress updates using SSE"""
    form = UploadForm()
    
    if form.validate_on_submit():
        # Check if the post request has the file part
        if 'file' not in request.files:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'error': 'No file part'})
            flash('No file part', 'danger')
            return redirect(request.url)
            
        file = request.files['file']
        
        # If user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'error': 'No selected file'})
            flash('No selected file', 'danger')
            return redirect(request.url)
            
        if file and allowed_file(file.filename):
            # Generate a unique task ID
            task_id = generate_task_id()
            
            # Secure the filename and save the file
            original_filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            stored_filename = f"{timestamp}_{original_filename}"
            upload_folder = ensure_upload_folder()
            file_path = os.path.join(upload_folder, stored_filename)
            file.save(file_path)
            
            # Create a database record for this upload
            file_upload = FileUpload(
                task_id=task_id,
                original_filename=original_filename,
                stored_filename=stored_filename,
                status='pending',
                user_id=current_user.id if current_user.is_authenticated else None
            )
            db.session.add(file_upload)
            db.session.commit()
            
            # Initialize task status
            update_task_status(task_id, {
                'status': 'pending',
                'message': 'Task queued',
                'file_path': file_path,
                'original_filename': original_filename
            })
            
            # Submit the task to the executor
            executor.submit(
                process_excel_file,
                file_path,
                task_id,
                current_user.id if current_user.is_authenticated else None
            )
            
            # Check if this is an AJAX request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': True,
                    'task_id': task_id,
                    'message': 'File uploaded and processing started'
                })
            
            # Redirect to the task status page for regular form submissions
            return redirect(url_for('esg_scores.task_status', task_id=task_id))
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'error': 'File type not allowed'})
            flash('File type not allowed. Please upload an Excel file (.xlsx, .xls)', 'danger')
            return redirect(request.url)
    
    # Get user's previous uploads
    user_uploads = []
    if current_user.is_authenticated:
        user_uploads = FileUpload.query.filter_by(user_id=current_user.id).order_by(FileUpload.created_at.desc()).limit(10).all()
    
    return render_template('esg_scores/excel_updater.html', form=form, user_uploads=user_uploads)

@bp.route('/task-status/<task_id>')
@login_required
def task_status(task_id):
    """Page to display task status with SSE updates"""
    # Get initial task status
    status = get_task_status(task_id)
    
    # Get file upload record
    file_upload = FileUpload.query.filter_by(task_id=task_id).first()
    
    if not file_upload:
        flash('Task not found', 'danger')
        return redirect(url_for('esg_scores.excel_updater'))
    
    # Check if the task belongs to the current user
    if file_upload.user_id and file_upload.user_id != current_user.id and not current_user.is_admin:
        flash('You do not have permission to view this task', 'danger')
        return redirect(url_for('esg_scores.excel_updater'))
    
    return render_template(
        'esg_scores/task_status.html',
        task_id=task_id,
        initial_status=status,
        file_upload=file_upload
    )

@bp.route('/sse-stream/<task_id>')
def sse_task_stream(task_id):
    """SSE stream for task updates"""
    return sse_stream(task_id, task_tracker)

@bp.route('/task-status-api/<task_id>')
def task_status_api(task_id):
    """API endpoint to get current task status"""
    status = get_task_status(task_id)
    return jsonify(status)

@bp.route('/download/<task_id>')
@login_required
def download_file(task_id):
    """Download a processed Excel file using task_id"""
    # Get the file upload record by task_id
    file_upload = FileUpload.query.filter_by(task_id=task_id).first()
    
    if not file_upload or not file_upload.output_filename:
        flash('File not found or processing not complete', 'danger')
        return redirect(url_for('esg_scores.excel_updater'))
    
    upload_folder = current_app.config.get('UPLOAD_FOLDER')
    filename = file_upload.output_filename
    
    # Check if the file exists
    file_path = os.path.join(upload_folder, filename)
    if not os.path.exists(file_path):
        flash('File not found', 'danger')
        return redirect(url_for('esg_scores.excel_updater'))
    
    # Check if the user has permission to download this file
    if file_upload.user_id and file_upload.user_id != current_user.id and not current_user.is_admin:
        flash('You do not have permission to download this file', 'danger')
        return redirect(url_for('esg_scores.excel_updater'))
    
    # Log the download
    current_app.logger.info(f"User {current_user.id} downloading file: {filename}")
    
    # Send the file with explicit Content-Disposition header
    response = send_from_directory(
        upload_folder,
        filename,
        as_attachment=True,
        download_name=file_upload.original_filename.replace('.xlsx', '_updated.xlsx')
    )
    response.headers['Content-Disposition'] = f'attachment; filename="{file_upload.original_filename.replace(".xlsx", "_updated.xlsx")}"'
    return response

@bp.route('/cancel-task/<task_id>', methods=['POST'])
@login_required
def cancel_task_route(task_id):
    """Cancel a running task"""
    # Check if the task belongs to the current user
    file_upload = FileUpload.query.filter_by(task_id=task_id).first()
    
    if not file_upload:
        return jsonify({'success': False, 'message': 'Task not found'})
    
    if file_upload.user_id and file_upload.user_id != current_user.id and not current_user.is_admin:
        return jsonify({'success': False, 'message': 'You do not have permission to cancel this task'})
    
    # Cancel the task
    success = cancel_task(task_id)
    
    if success:
        # Update the database record
        file_upload.status = 'cancelled'
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Task cancelled'})
    else:
        return jsonify({'success': False, 'message': 'Failed to cancel task'})
    
@bp.route('/error/<error_type>')
def error_page(error_type):
    """Display error page with details"""
    error_message = request.args.get('message', 'An unknown error occurred')
    error_details = request.args.get('details', '')
    
    # Log the error
    log_error(
        error_type=error_type,
        error_message=error_message,
        details=error_details,
        user_id=current_user.id if current_user.is_authenticated else None
    )
    
    return render_template(
        'esg_scores/error.html',
        error_type=error_type,
        error_message=error_message,
        error_details=error_details
    )

@bp.route('/stream-scores/<company_name>')
def stream_scores(company_name):
    """Stream ESG scores using Server-Sent Events"""
    year = request.args.get('year')
    
    # Log the search activity
    user_id = current_user.id if current_user.is_authenticated else 'anonymous'
    log_data = {
        "company_name": company_name,
        "action": "stream_scores"
    }
    if year:
        log_data["year"] = year
        
    log_user_activity(
        user_id=user_id,
        action="esg_score_stream",
        details=log_data
    )
    
    return stream_all_scores(company_name, year)

@bp.route('/file-uploads')
@login_required
def file_uploads():
    """View all file uploads for the current user with pagination"""
    # Get page number from request args, default to 1
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Number of items per page
    
    # Get user's uploads with pagination
    if current_user.is_admin:
        # Admins can see all uploads
        pagination = FileUpload.query.order_by(FileUpload.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False)
    else:
        # Regular users can only see their own uploads
        pagination = FileUpload.query.filter_by(user_id=current_user.id).order_by(
            FileUpload.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    
    uploads = pagination.items
    
    return render_template('esg_scores/file_uploads.html', 
                          uploads=uploads, 
                          pagination=pagination)

@bp.route('/delete-upload/<upload_id>', methods=['POST'])
@login_required
def delete_upload(upload_id):
    """Delete a file upload record"""
    file_upload = FileUpload.query.get_or_404(upload_id)
    
    # Check if the user has permission to delete this upload
    if file_upload.user_id != current_user.id and not current_user.is_admin:
        return jsonify({'success': False, 'message': 'You do not have permission to delete this upload'})
    
    # Check if the upload is currently processing
    if file_upload.status in ['pending', 'processing']:
        # Try to cancel the task first
        cancel_task(file_upload.task_id)
    
    # Maximum retry attempts for file deletion
    max_retries = 3
    retry_count = 0
    retry_delay = 1  # seconds
    
    try:
        # Delete the stored file if it exists
        upload_folder = current_app.config.get('UPLOAD_FOLDER')
        file_deletion_errors = []
        
        # Function to attempt file deletion with retries
        def try_delete_file(file_path):
            nonlocal retry_count
            
            while retry_count < max_retries:
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        return True
                except PermissionError as e:
                    # File might be locked by another process
                    current_app.logger.warning(f"Permission error on attempt {retry_count+1} deleting {file_path}: {e}")
                    retry_count += 1
                    if retry_count < max_retries:
                        import time
                        time.sleep(retry_delay)
                    else:
                        file_deletion_errors.append(f"Could not delete {os.path.basename(file_path)} after {max_retries} attempts")
                        return False
                except Exception as e:
                    current_app.logger.error(f"Error deleting {file_path}: {e}")
                    file_deletion_errors.append(f"Error deleting {os.path.basename(file_path)}: {str(e)}")
                    return False
            return False
        
        # Try to delete input file if it exists
        if file_upload.stored_filename:
            input_path = os.path.join(upload_folder, file_upload.stored_filename)
            try_delete_file(input_path)
        
        # Reset retry count for output file
        retry_count = 0
        
        # Try to delete output file if it exists
        if file_upload.output_filename:
            output_path = os.path.join(upload_folder, file_upload.output_filename)
            try_delete_file(output_path)
            
            # Also try to delete any updated ESG scores file based on output name
            try:
                # Check for task_id based updated file
                updated_file_taskid = os.path.join(upload_folder, f"updated_esg_scores_{file_upload.task_id}.xlsx")
                if os.path.exists(updated_file_taskid):
                    retry_count = 0  # Reset for new file
                    try_delete_file(updated_file_taskid)
                
                # Check for timestamp based updated file
                timestamp_match = re.search(r'(\d{8}_\d{6})', file_upload.output_filename)
                if timestamp_match:
                    timestamp = timestamp_match.group(1)
                    updated_file_ts = os.path.join(upload_folder, f"updated_esg_scores_{timestamp}.xlsx")
                    if os.path.exists(updated_file_ts):
                        retry_count = 0  # Reset for new file
                        try_delete_file(updated_file_ts)
            except Exception as e:
                current_app.logger.error(f"Error trying to delete updated ESG files: {e}")
                file_deletion_errors.append(f"Error deleting updated ESG files: {str(e)}")
        
        # Attempt to force close any open file handles (Windows-specific)
        import platform
        if platform.system() == 'Windows' and file_deletion_errors:
            try:
                # Force Python garbage collection to release file handles
                import gc
                gc.collect()
                
                # Optional: Add a small delay to give time for handles to be released
                import time
                time.sleep(0.5)
            except Exception as e:
                current_app.logger.error(f"Error during garbage collection: {e}")
        
        # Delete the database record even if file deletion had issues
        db.session.delete(file_upload)
        db.session.commit()
        
        # Return success with warnings if applicable
        if file_deletion_errors:
            message = "Upload record deleted, but some files could not be deleted and may require manual cleanup."
            current_app.logger.warning(f"Partial deletion success for upload ID {upload_id}: {file_deletion_errors}")
            return jsonify({'success': True, 'message': message, 'warnings': file_deletion_errors})
        else:
            return jsonify({'success': True, 'message': 'Upload deleted successfully'})
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting upload: {e}")
        return jsonify({'success': False, 'message': f'Error deleting upload: {str(e)}'})


@bp.route('/view-results/<task_id>')
@login_required
def view_results(task_id):
    """View the results of a processed file with sheet selection"""
    file_upload = FileUpload.query.filter_by(task_id=task_id).first_or_404()

    if file_upload.user_id != current_user.id and not current_user.is_admin:
        flash('You do not have permission to view this upload', 'danger')
        return redirect(url_for('esg_scores.file_uploads'))

    if file_upload.status != 'complete':
        flash('This file is not yet processed', 'warning')
        return redirect(url_for('esg_scores.task_status', task_id=task_id))

    try:
        upload_folder = current_app.config.get('UPLOAD_FOLDER')
        original_filename = file_upload.output_filename
        filename_without_ext = os.path.splitext(original_filename)[0]

        # Determine the correct file path (prefer updated file)
        # Look for updated_esg_scores files first based on task_id
        updated_file_pattern_taskid = f"updated_esg_scores_{task_id}.xlsx"
        potential_updated_path_taskid = os.path.join(upload_folder, updated_file_pattern_taskid)

        # Then look based on timestamp if task_id version doesn't exist
        updated_file_path = None
        timestamp_match = re.search(r'(\d{8}_\d{6})', original_filename)
        if timestamp_match:
            timestamp = timestamp_match.group(1)
            updated_file_pattern_ts = f"updated_esg_scores_{timestamp}.xlsx"
            potential_updated_path_ts = os.path.join(upload_folder, updated_file_pattern_ts)
            if os.path.exists(potential_updated_path_ts):
                updated_file_path = potential_updated_path_ts

        # Prioritize task_id match if it exists
        if os.path.exists(potential_updated_path_taskid):
             updated_file_path = potential_updated_path_taskid

        # Determine final file path and if it's the updated one
        if updated_file_path and os.path.exists(updated_file_path):
             file_path = updated_file_path
             using_updated_file = True
             current_app.logger.info(f"Using updated file: {file_path}")
        else:
             file_path = os.path.join(upload_folder, original_filename)
             using_updated_file = False
             current_app.logger.info(f"Using original/processed file: {file_path}")

        if not os.path.exists(file_path):
            flash(f'Result file not found at expected location: {file_path}', 'danger')
            current_app.logger.error(f"Result file not found: {file_path}")
            return redirect(url_for('esg_scores.file_uploads'))

        # --- Define ESG Indicators Early ---
        esg_indicators = ['s&p', 'sustainalytics', 'iss', 'lseg', 'msci']

        # --- Sheet Handling Logic ---
        # Use context managers to ensure file handles are closed
        available_sheet_names = []
        excel_file = None
        
        try:
            # Open Excel file for reading sheet names only
            excel_file = pd.ExcelFile(file_path)
            available_sheet_names = excel_file.sheet_names.copy()  # Copy sheet names
        except Exception as e:
            current_app.logger.error(f"Error reading Excel file sheets: {e}", exc_info=True)
            flash(f'Error reading Excel file: {str(e)}', 'danger')
            return redirect(url_for('esg_scores.file_uploads'))
        finally:
            # Close the Excel file handle explicitly
            if excel_file is not None:
                excel_file.close()
                del excel_file

        if not available_sheet_names:
             flash('The Excel file appears to be empty or has no sheets.', 'warning')
             return render_template(
                 'esg_scores/view_results.html',
                 file_upload=file_upload,
                 results={'sheet_names': [], 'current_sheet': None, 'summary_headers': [], 'summary_rows': [], 'using_updated_file': using_updated_file, 'found_scores': False},
                 error_message="No sheets found in the file."
             )

        # Get requested sheet from query parameters
        requested_sheet = request.args.get('sheet')
        current_sheet_name = None

        # Validate requested sheet or determine default
        if requested_sheet and requested_sheet in available_sheet_names:
            current_sheet_name = requested_sheet
            current_app.logger.info(f"Using requested sheet: {current_sheet_name}")
        else:
            if requested_sheet:
                 flash(f"Sheet '{requested_sheet}' not found. Displaying default sheet.", 'warning')
                 current_app.logger.warning(f"Requested sheet '{requested_sheet}' not found in {available_sheet_names}.")

            # Default logic: Try to find a sheet with ESG scores first
            found_scores_sheet_name = None
            # esg_indicators is now defined above and accessible here
            for sheet in available_sheet_names:
                try:
                    # Only read headers to check for ESG columns
                    with pd.ExcelFile(file_path) as temp_excel:
                        sample_df = pd.read_excel(temp_excel, sheet_name=sheet, nrows=0)
                        columns = sample_df.columns.tolist()
                        has_esg_columns = any(any(indicator in col.lower() for indicator in esg_indicators) for col in columns)
                        has_company_col = any('company' in col.lower() or 'name' in col.lower() for col in columns)
                        if has_company_col and (has_esg_columns or len(columns) > 1):
                             found_scores_sheet_name = sheet
                             current_app.logger.info(f"Found potential ESG scores in default sheet: {sheet}")
                             break
                except Exception as e:
                    current_app.logger.warning(f"Could not read header for sheet '{sheet}': {e}")
                    continue

            if found_scores_sheet_name:
                 current_sheet_name = found_scores_sheet_name
            else:
                 current_sheet_name = available_sheet_names[0] # Fallback to the first sheet
                 current_app.logger.info(f"No specific ESG sheet found, defaulting to first sheet: {current_sheet_name}")

        # --- Read Data from Selected Sheet ---
        current_app.logger.info(f"Reading data from sheet: '{current_sheet_name}' in file: {file_path}")
        
        # Use a context manager to ensure the file is closed after reading
        df = None
        try:
            with pd.ExcelFile(file_path) as excel:
                df = pd.read_excel(excel, sheet_name=current_sheet_name)
        except Exception as e:
            current_app.logger.error(f"Error reading sheet '{current_sheet_name}': {e}", exc_info=True)
            flash(f'Error reading sheet: {str(e)}', 'danger')
            return redirect(url_for('esg_scores.file_uploads'))

        # Check again if this *specific* selected sheet has scores (for the badge)
        columns = df.columns.tolist()
        # esg_indicators is now defined above and accessible here
        has_esg_columns_in_current = any(any(indicator in col.lower() for indicator in esg_indicators) for col in columns)
        has_company_col_in_current = any('company' in col.lower() or 'name' in col.lower() for col in columns)
        # Corrected logic: A sheet might have scores even without a 'company' column if it's obvious from context
        # Let's just check for the presence of *any* ESG indicator column for the badge
        found_scores_in_current_sheet = has_esg_columns_in_current

        # Process DataFrame
        df = df.fillna('')
        for col in df.columns:
            try:
                df[col] = df[col].astype(str)
            except Exception as e:
                 current_app.logger.warning(f"Could not convert column '{col}' to string, attempting safe conversion: {e}")
                 df[col] = df[col].apply(lambda x: str(x) if pd.notna(x) else '')

        summary_headers = df.columns.tolist()
        summary_rows = df.values.tolist()
        
        # Clean up DataFrame reference to help with garbage collection
        del df

        results = {
            'summary_headers': summary_headers,
            'summary_rows': summary_rows,
            'file_path': file_path,
            'using_updated_file': using_updated_file,
            'sheet_names': available_sheet_names,
            'current_sheet': current_sheet_name,
            'found_scores': found_scores_in_current_sheet # Indicate if scores found in *this* sheet
        }

    except FileNotFoundError:
        flash(f'Result file not found.', 'danger')
        current_app.logger.error(f"FileNotFoundError trying to access results for task {task_id}")
        return redirect(url_for('esg_scores.file_uploads'))
    except Exception as e:
        current_app.logger.error(f"Error processing results for task {task_id}: {e}", exc_info=True)
        flash(f'Error reading or parsing results file: {str(e)}', 'danger')
        # Pass file_upload even on error so breadcrumbs etc. work
        return render_template(
             'esg_scores/view_results.html',
             file_upload=file_upload,
             results={'sheet_names': [], 'current_sheet': None, 'summary_headers': [], 'summary_rows': [], 'using_updated_file': False, 'found_scores': False},
             error_message=f"Error processing file: {str(e)}"
         )

    # Explicitly call garbage collection to help free resources
    import gc
    gc.collect()

    return render_template(
        'esg_scores/view_results.html',
        file_upload=file_upload,
        results=results
    )

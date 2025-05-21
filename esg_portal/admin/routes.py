"""
Admin routes for the ESG News Portal
"""
import os
import json
from datetime import datetime, timedelta
from functools import wraps
from flask import render_template, redirect, url_for, flash, request, current_app, jsonify, send_file
from flask_login import login_required, current_user
from sqlalchemy import desc, func

from esg_portal.admin import bp
from esg_portal import db, cache
from esg_portal.models.user import User
from esg_portal.models.file_upload import FileUpload
from esg_portal.utils.logging_utils import user_logger, error_logger

# Check if cache is available with Redis or use a no-op decorator
def conditional_cache(timeout=60):
    """Conditionally apply cache if Redis is available, otherwise do nothing"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if current_app.config.get('REDIS_AVAILABLE', False):
                # Only apply caching if Redis is available
                return cache.cached(timeout=timeout)(f)(*args, **kwargs)
            else:
                # Otherwise just call the function
                return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    """
    Decorator to ensure that only admin users can access a route
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('core.index'))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/')
@login_required
@admin_required
@conditional_cache(timeout=60)  # Cache for 1 minute if Redis is available
def dashboard():
    """Admin dashboard home page"""
    # Get user statistics
    total_users = User.query.count()
    active_users = User.query.filter(User.last_login > (datetime.utcnow() - timedelta(days=30))).count()
    new_users = User.query.filter(User.created_at > (datetime.utcnow() - timedelta(days=30))).count()
    
    # Get recent users
    recent_users = User.query.order_by(desc(User.created_at)).limit(5).all()
    
    # Get user activity by date (last 7 days)
    date_labels = [(datetime.utcnow() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7, 0, -1)]
    
    # Get log file paths
    logs_dir = os.path.join(current_app.instance_path, 'logs')
    user_log_path = os.path.join(logs_dir, 'user_activity.json')
    error_log_path = os.path.join(logs_dir, 'errors.log')
    
    # Check if log files exist
    user_log_exists = os.path.exists(user_log_path)
    error_log_exists = os.path.exists(error_log_path)
    
    # Get log file sizes
    user_log_size = os.path.getsize(user_log_path) if user_log_exists else 0
    error_log_size = os.path.getsize(error_log_path) if error_log_exists else 0
    
    # Format sizes for display
    def format_size(size_bytes):
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.2f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.2f} MB"
    
    user_log_size_formatted = format_size(user_log_size)
    error_log_size_formatted = format_size(error_log_size)
    
    return render_template(
        'admin/dashboard.html',
        total_users=total_users,
        active_users=active_users,
        new_users=new_users,
        recent_users=recent_users,
        date_labels=date_labels,
        user_log_exists=user_log_exists,
        error_log_exists=error_log_exists,
        user_log_size=user_log_size_formatted,
        error_log_size=error_log_size_formatted
    )

@bp.route('/users')
@login_required
@admin_required
def users():
    """User management page"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    search_term = request.args.get('search', '')
    sort_by = request.args.get('sort', 'created_at')
    sort_order = request.args.get('order', 'desc')
    
    # Cache key based on query parameters
    cache_key = f"users_page_{page}_search_{search_term}_sort_{sort_by}_{sort_order}"
    
    # Try to get from cache first if Redis is available
    cached_data = None
    if current_app.config.get('REDIS_AVAILABLE', False) and not search_term:
        cached_data = cache.get(cache_key)
    
    # If we have cached data and it's not a search, return it
    if cached_data:
        return cached_data
    
    # Build query
    query = User.query
    
    # Apply search filter if provided
    if search_term:
        search_term = f"%{search_term}%"
        query = query.filter(
            db.or_(
                User.username.ilike(search_term),
                User.email.ilike(search_term),
                User.first_name.ilike(search_term),
                User.last_name.ilike(search_term)
            )
        )
    
    # Apply sorting
    if sort_by == 'username':
        query = query.order_by(User.username.desc() if sort_order == 'desc' else User.username.asc())
    elif sort_by == 'email':
        query = query.order_by(User.email.desc() if sort_order == 'desc' else User.email.asc())
    elif sort_by == 'last_login':
        query = query.order_by(User.last_login.desc() if sort_order == 'desc' else User.last_login.asc())
    else:  # Default to created_at
        query = query.order_by(User.created_at.desc() if sort_order == 'desc' else User.created_at.asc())
    
    # Paginate results
    users_pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    result = render_template(
        'admin/users.html',
        users=users_pagination.items,
        pagination=users_pagination,
        search_term=search_term,
        sort_by=sort_by,
        sort_order=sort_order
    )
    
    # Cache the result if not a search and Redis is available
    if not search_term and current_app.config.get('REDIS_AVAILABLE', False):
        try:
            cache.set(cache_key, result, timeout=60)  # Cache for 1 minute
        except Exception as e:
            current_app.logger.warning(f"Failed to cache data: {str(e)}")
    
    return result

@bp.route('/user/<int:id>')
@login_required
@admin_required
def user_detail(id):
    """User detail page"""
    user = User.query.get_or_404(id)
    
    # Get user activity logs
    user_logs = []
    logs_dir = os.path.join(current_app.instance_path, 'logs')
    user_log_path = os.path.join(logs_dir, 'user_activity.json')
    
    if os.path.exists(user_log_path):
        try:
            # Get file size to determine if we should use a more efficient approach
            file_size = os.path.getsize(user_log_path)
            max_logs = 50  # Maximum number of logs to display
            
            # For large files, use a more efficient approach
            if file_size > 1024 * 1024:  # If file is larger than 1MB
                # Use grep-like approach to find relevant logs
                user_id_str = f'"user_id": {id}'
                found_logs = 0
                
                with open(user_log_path, 'rb') as f:
                    # Start from the end of the file
                    f.seek(0, os.SEEK_END)
                    file_size = f.tell()
                    
                    # Read in chunks from the end
                    chunk_size = min(file_size, 1024 * 1024)  # 1MB or file size, whichever is smaller
                    position = file_size
                    
                    while position > 0 and found_logs < max_logs:
                        # Move back by chunk size
                        position = max(0, position - chunk_size)
                        f.seek(position)
                        
                        # Read chunk
                        chunk = f.read(chunk_size).decode('utf-8')
                        lines = chunk.splitlines()
                        
                        # If we're not at the start of the file and the first line is incomplete,
                        # it will be completed in the next iteration
                        if position > 0 and len(lines) > 0:
                            lines = lines[1:]
                        
                        # Process lines in reverse (newest first)
                        for line in reversed(lines):
                            if not line.strip():
                                continue
                                
                            # Quick check if this line might contain the user ID
                            if str(id) in line:
                                try:
                                    log_entry = json.loads(line)
                                    if str(log_entry.get('user_id', '')) == str(id):
                                        # Add username to log entry
                                        log_entry['username'] = user.username
                                        user_logs.append(log_entry)
                                        found_logs += 1
                                        
                                        if found_logs >= max_logs:
                                            break
                                except json.JSONDecodeError:
                                    continue
            else:
                # For smaller files, read the whole file
                with open(user_log_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if not line:  # Skip empty lines
                            continue
                        try:
                            log_entry = json.loads(line)
                            try:
                                log_user_id = str(log_entry.get('user_id', ''))
                                if log_user_id and log_user_id == str(id):
                                    # Add username to log entry
                                    log_entry['username'] = user.username
                                    user_logs.append(log_entry)
                                    
                                    # Limit to the most recent logs
                                    if len(user_logs) >= max_logs:
                                        break
                            except (ValueError, TypeError):
                                continue
                        except json.JSONDecodeError as e:
                            current_app.logger.error(f"Error parsing log entry: {line[:100]}... - {str(e)}")
                            continue
        except Exception as e:
            current_app.logger.error(f"Error reading log file: {str(e)}")
            flash(f"Error reading log file: {str(e)}", "danger")
    
    # Sort logs by timestamp (newest first)
    user_logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    
    # Limit to the most recent logs
    user_logs = user_logs[:50]
    
    return render_template(
        'admin/user_detail.html',
        user=user,
        user_logs=user_logs
    )

@bp.route('/user/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(id):
    """Edit user page"""
    user = User.query.get_or_404(id)
    
    if request.method == 'POST':
        # Update user data
        user.username = request.form.get('username')
        user.email = request.form.get('email')
        user.first_name = request.form.get('first_name')
        user.last_name = request.form.get('last_name')
        user.is_admin = 'is_admin' in request.form
        user.is_active = 'is_active' in request.form
        
        # Update password if provided
        new_password = request.form.get('password')
        if new_password:
            user.set_password(new_password)
        
        db.session.commit()
        flash(f'User {user.username} has been updated.', 'success')
        return redirect(url_for('admin.user_detail', id=user.id))
    
    return render_template(
        'admin/edit_user.html',
        user=user
    )

@bp.route('/user/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_user():
    """Create new user page"""
    if request.method == 'POST':
        # Check if username or email already exists
        username = request.form.get('username')
        email = request.form.get('email')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return redirect(url_for('admin.create_user'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists.', 'danger')
            return redirect(url_for('admin.create_user'))
        
        # Create new user
        user = User(
            username=username,
            email=email,
            first_name=request.form.get('first_name'),
            last_name=request.form.get('last_name'),
            is_admin='is_admin' in request.form,
            is_active='is_active' in request.form
        )
        
        # Set password
        password = request.form.get('password')
        if password:
            user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash(f'User {user.username} has been created.', 'success')
        return redirect(url_for('admin.users'))
    
    return render_template('admin/create_user.html')

@bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    if current_user.id == user_id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('admin.users'))
    
    user = User.query.get_or_404(user_id)
    
    try:
        # First, delete all file uploads associated with this user
        file_uploads = FileUpload.query.filter_by(user_id=user_id).all()
        for upload in file_uploads:
            # Optionally: delete the actual files from storage
            # if os.path.exists(upload.file_path):
            #     os.remove(upload.file_path)
            db.session.delete(upload)
        
        # Now delete the user
        db.session.delete(user)
        db.session.commit()
        flash(f'User {user.username} has been deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting user: {str(e)}', 'danger')
        current_app.logger.error(f"Error deleting user {user_id}: {str(e)}")
    
    return redirect(url_for('admin.users'))

@bp.route('/logs')
@login_required
@admin_required
def logs():
    """View logs page"""
    log_type = request.args.get('type', 'user')
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    logs_dir = os.path.join(current_app.instance_path, 'logs')
    
    if log_type == 'user':
        log_path = os.path.join(logs_dir, 'user_activity.json')
        
        # Check if file exists
        if not os.path.exists(log_path):
            flash("No logs found.", "info")
            return render_template(
                'admin/logs.html',
                log_type=log_type,
                logs=[],
                page=1,
                total_pages=1,
                total_logs=0
            )
        
        # Get file size to determine if we should use a more efficient approach
        file_size = os.path.getsize(log_path)
        
        # For large files, use a more efficient approach
        if file_size > 1024 * 1024:  # If file is larger than 1MB
            # Use tail approach to get only the most recent logs
            log_entries = []
            try:
                # Read only the last N lines of the file
                with open(log_path, 'rb') as f:
                    # Seek to the end of the file
                    f.seek(0, os.SEEK_END)
                    # Buffer for the last chunk of the file
                    buffer_size = min(file_size, 1024 * 1024)  # 1MB or file size, whichever is smaller
                    
                    # Read the last chunk of the file
                    if buffer_size > 0:
                        f.seek(-buffer_size, os.SEEK_END)
                        lines = f.read().decode('utf-8').splitlines()
                        
                        # Process the lines
                        for line in reversed(lines):  # Process from newest to oldest
                            if not line.strip():
                                continue
                            try:
                                log_entry = json.loads(line)
                                
                                # Add username to log entry if user_id is a number
                                try:
                                    user_id = log_entry.get('user_id')
                                    if user_id and isinstance(user_id, (int, str)) and str(user_id).isdigit():
                                        user = User.query.get(int(user_id))
                                        if user:
                                            log_entry['username'] = user.username
                                        else:
                                            log_entry['username'] = f"Unknown (ID: {user_id})"
                                    else:
                                        log_entry['username'] = 'Anonymous'
                                except (ValueError, TypeError):
                                    log_entry['username'] = 'Anonymous'
                                    
                                log_entries.append(log_entry)
                                
                                # Stop once we have enough entries for the current page plus some buffer
                                if len(log_entries) >= per_page * (page + 1):
                                    break
                            except json.JSONDecodeError:
                                continue
            except Exception as e:
                current_app.logger.error(f"Error reading log file: {str(e)}")
                flash(f"Error reading log file: {str(e)}", "danger")
        else:
            # For smaller files, read the whole file
            log_entries = []
            try:
                with open(log_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if not line:  # Skip empty lines
                            continue
                        try:
                            log_entry = json.loads(line)
                            
                            # Add username to log entry if user_id is a number
                            try:
                                user_id = log_entry.get('user_id')
                                if user_id and isinstance(user_id, (int, str)) and str(user_id).isdigit():
                                    user = User.query.get(int(user_id))
                                    if user:
                                        log_entry['username'] = user.username
                                    else:
                                        log_entry['username'] = f"Unknown (ID: {user_id})"
                                else:
                                    log_entry['username'] = 'Anonymous'
                            except (ValueError, TypeError):
                                log_entry['username'] = 'Anonymous'
                                
                            log_entries.append(log_entry)
                        except json.JSONDecodeError as e:
                            current_app.logger.error(f"Error parsing log entry: {line[:100]}... - {str(e)}")
                            continue
            except Exception as e:
                current_app.logger.error(f"Error reading log file: {str(e)}")
                flash(f"Error reading log file: {str(e)}", "danger")
        
        # Sort logs by timestamp (newest first)
        log_entries.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # Simple pagination
        total_logs = len(log_entries)
        total_pages = max(1, (total_logs + per_page - 1) // per_page)
        start_idx = (page - 1) * per_page
        end_idx = min(start_idx + per_page, total_logs)
        
        paginated_logs = log_entries[start_idx:end_idx]
        
        return render_template(
            'admin/logs.html',
            log_type=log_type,
            logs=paginated_logs,
            page=page,
            total_pages=total_pages,
            total_logs=total_logs
        )
    
    elif log_type == 'error':
        log_path = os.path.join(logs_dir, 'errors.log')
        log_entries = []
        
        if os.path.exists(log_path):
            with open(log_path, 'r') as f:
                log_content = f.read()
                # Split by log entries (assuming each entry starts with a timestamp)
                import re
                log_entries = re.split(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})', log_content)
                
                # Combine timestamp with content
                formatted_entries = []
                for i in range(1, len(log_entries), 2):
                    if i+1 < len(log_entries):
                        formatted_entries.append({
                            'timestamp': log_entries[i],
                            'content': log_entries[i+1]
                        })
                
                log_entries = formatted_entries
        
        # Simple pagination
        total_logs = len(log_entries)
        total_pages = (total_logs + per_page - 1) // per_page
        start_idx = (page - 1) * per_page
        end_idx = min(start_idx + per_page, total_logs)
        
        paginated_logs = log_entries[start_idx:end_idx]
        
        return render_template(
            'admin/logs.html',
            log_type=log_type,
            logs=paginated_logs,
            page=page,
            total_pages=total_pages,
            total_logs=total_logs
        )
    
    else:
        flash('Invalid log type.', 'danger')
        return redirect(url_for('admin.dashboard'))

@bp.route('/logs/download')
@login_required
@admin_required
def download_logs():
    """Download logs"""
    log_type = request.args.get('type', 'user')
    
    logs_dir = os.path.join(current_app.instance_path, 'logs')
    
    if log_type == 'user':
        log_path = os.path.join(logs_dir, 'user_activity.json')
        if os.path.exists(log_path):
            return send_file(
                log_path,
                as_attachment=True,
                download_name=f'user_activity_{datetime.now().strftime("%Y%m%d")}.json'
            )
    
    elif log_type == 'error':
        log_path = os.path.join(logs_dir, 'errors.log')
        if os.path.exists(log_path):
            return send_file(
                log_path,
                as_attachment=True,
                download_name=f'errors_{datetime.now().strftime("%Y%m%d")}.log'
            )
    
    flash('Log file not found.', 'danger')
    return redirect(url_for('admin.logs', type=log_type))
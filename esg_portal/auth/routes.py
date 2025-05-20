"""
Authentication routes for user management
"""
from datetime import datetime
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required

from esg_portal.auth import bp
from esg_portal.auth.forms import LoginForm, RegistrationForm, ProfileForm
from esg_portal.models.user import User
from esg_portal import db
from esg_portal.utils.logging_utils import log_user_activity, log_error

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login page"""
    if current_user.is_authenticated:
        return redirect(url_for('core.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password', 'danger')
            # Log failed login attempt
            log_user_activity(
                user_id=form.username.data,
                action="login",
                status="failure",
                details={"reason": "Invalid username or password"}
            )
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=form.remember_me.data)
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        # Log successful login
        log_user_activity(
            user_id=user.id,
            action="login",
            status="success",
            details={"remember_me": form.remember_me.data}
        )
        
        next_page = request.args.get('next')
        if not next_page or next_page.startswith('http') or next_page.startswith('//'):
            next_page = url_for('core.index')
        
        return redirect(next_page)
    
    return render_template('auth/login.html', title='Sign In', form=form)

@bp.route('/logout')
def logout():
    """User logout"""
    if current_user.is_authenticated:
        # Log logout
        log_user_activity(
            user_id=current_user.id,
            action="logout",
            status="success"
        )
    
    logout_user()
    return redirect(url_for('core.index'))

@bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page"""
    if current_user.is_authenticated:
        return redirect(url_for('core.index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            user = User(
                username=form.username.data,
                email=form.email.data,
                first_name=form.first_name.data,
                last_name=form.last_name.data
            )
            user.set_password(form.password.data)
            
            db.session.add(user)
            db.session.commit()
            
            # Log successful registration
            log_user_activity(
                user_id=user.id,
                action="register",
                status="success",
                details={
                    "username": user.username,
                    "email": user.email
                }
            )
            
            flash('Congratulations, you are now a registered user!', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            log_error(e, additional_info={"form_data": {
                "username": form.username.data,
                "email": form.email.data
            }})
            flash('An error occurred during registration. Please try again.', 'danger')
    
    return render_template('auth/register.html', title='Register', form=form)

@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile page"""
    form = ProfileForm(obj=current_user)
    
    if form.validate_on_submit():
        try:
            # Track changes for logging
            changes = {}
            if current_user.first_name != form.first_name.data:
                changes["first_name"] = {"old": current_user.first_name, "new": form.first_name.data}
            if current_user.last_name != form.last_name.data:
                changes["last_name"] = {"old": current_user.last_name, "new": form.last_name.data}
            if current_user.email != form.email.data:
                changes["email"] = {"old": current_user.email, "new": form.email.data}
            if form.password.data:
                changes["password"] = {"changed": True}
            
            # Update user data
            current_user.first_name = form.first_name.data
            current_user.last_name = form.last_name.data
            current_user.email = form.email.data
            current_user.preferred_categories = ','.join(form.preferred_categories.data)
            current_user.email_notifications = form.email_notifications.data
            
            if form.password.data:
                current_user.set_password(form.password.data)
            
            db.session.commit()
            
            # Log profile update
            log_user_activity(
                user_id=current_user.id,
                action="profile_update",
                status="success",
                details={"changes": changes}
            )
            
            flash('Your profile has been updated.', 'success')
            return redirect(url_for('auth.profile'))
        except Exception as e:
            db.session.rollback()
            log_error(e, user_id=current_user.id)
            flash('An error occurred while updating your profile. Please try again.', 'danger')
    
    return render_template('auth/profile.html', title='Profile', form=form) 
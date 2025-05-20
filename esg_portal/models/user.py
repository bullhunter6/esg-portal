"""
User model for authentication and personalization
"""
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from esg_portal import db, login_manager

class User(UserMixin, db.Model):
    """User model for authentication and personalization"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True, nullable=False)
    email = db.Column(db.String(120), unique=True, index=True, nullable=False)
    password = db.Column(db.String(255), nullable=True)  # Legacy column, kept for backward compatibility
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(64))
    last_name = db.Column(db.String(64))
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active_db = db.Column(db.Boolean, default=True, nullable=False) # Renamed column to avoid conflict
    
    # User preferences
    preferred_categories = db.Column(db.String(256))  # Comma-separated list of categories
    email_notifications = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def set_password(self, password):
        """Set the user's password hash"""
        self.password_hash = generate_password_hash(password)
        self.password = self.password_hash  # Also update the legacy password field
    
    def check_password(self, password):
        """Check if the provided password matches the hash"""
        return check_password_hash(self.password_hash, password)
    
    def get_full_name(self):
        """Return the user's full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username

    @property
    def is_active(self):
        """Return True if the user's account is active."""
        return self.is_active_db

    @is_active.setter
    def is_active(self, value):
        """Set the user's active status."""
        self.is_active_db = bool(value)

@login_manager.user_loader
def load_user(user_id):
    """Load a user for Flask-Login"""
    return User.query.get(int(user_id)) 
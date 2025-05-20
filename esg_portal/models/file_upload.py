"""
File Upload model for tracking uploaded files and their processing status
"""
from datetime import datetime
from esg_portal import db

class FileUpload(db.Model):
    """Model for tracking file uploads and processing status"""
    __tablename__ = 'file_uploads'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.String(36), unique=True, nullable=False)
    original_filename = db.Column(db.String(256), nullable=False)
    stored_filename = db.Column(db.String(256), nullable=False)
    output_filename = db.Column(db.String(256))
    status = db.Column(db.String(20), default='pending')  # pending, processing, complete, error, cancelled
    error_message = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<FileUpload {self.original_filename}>'
    
    def to_dict(self):
        """Convert file upload to dictionary for API responses"""
        return {
            'id': self.id,
            'task_id': self.task_id,
            'original_filename': self.original_filename,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'output_filename': self.output_filename
        }

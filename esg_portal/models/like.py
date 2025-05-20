"""
Like model for tracking user likes on content
"""
from datetime import datetime
from esg_portal import db
from flask import current_app

class Like(db.Model):
    """Model for tracking user likes on different content types"""
    __tablename__ = 'likes'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    content_type = db.Column(db.String(20), nullable=False, index=True)  # 'article', 'event', 'publication'
    content_id = db.Column(db.Integer, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # Define a unique constraint to prevent duplicate likes
    __table_args__ = (
        db.UniqueConstraint('user_id', 'content_type', 'content_id', name='unique_like'),
        db.Index('idx_content_type_id', 'content_type', 'content_id'),
    )
    
    def __repr__(self):
        return f'<Like {self.user_id} - {self.content_type} {self.content_id}>'
    
    @classmethod
    def is_liked(cls, user_id, content_type, content_id):
        """Check if a user has liked a specific content"""
        return cls.query.filter_by(
            user_id=user_id,
            content_type=content_type,
            content_id=content_id
        ).first() is not None
    
    @classmethod
    def toggle_like(cls, user_id, content_type, content_id):
        """Toggle like status for a user on specific content"""
        try:
            # Convert content_id to string if it's not already
            content_id = str(content_id)
            
            # Use a more efficient approach with a single query
            # Try to delete the like first - if it exists, it will be deleted
            deleted = db.session.query(cls).filter_by(
                user_id=user_id,
                content_type=content_type,
                content_id=content_id
            ).delete()
            
            # If nothing was deleted, add a new like
            if deleted == 0:
                new_like = cls(
                    user_id=user_id,
                    content_type=content_type,
                    content_id=content_id
                )
                db.session.add(new_like)
                db.session.commit()
                return True  # Liked
            else:
                db.session.commit()
                return False  # Unliked
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error toggling like: {e}")
            # If there was an error, check if the user has already liked the content
            is_liked = cls.is_liked(user_id, content_type, content_id)
            return is_liked
    
    @classmethod
    def get_user_likes(cls, user_id, content_type=None):
        """Get all likes for a user, optionally filtered by content type"""
        query = cls.query.filter_by(user_id=user_id)
        if content_type:
            query = query.filter_by(content_type=content_type)
        return query.order_by(cls.created_at.desc()).all()
    
    @classmethod
    def get_content_likes_count(cls, content_type, content_id):
        """Get the number of likes for a specific content"""
        return cls.query.filter_by(
            content_type=content_type,
            content_id=content_id
        ).count() 
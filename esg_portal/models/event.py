"""
Event model for ESG-related events
"""
from datetime import datetime
from esg_portal import db

class Event(db.Model):
    """Model for ESG-related events"""
    __tablename__ = 'events'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, nullable=False)
    # Use event_summary directly instead of summary
    event_summary = db.Column(db.Text)
    description = db.Column(db.Text)
    start_date = db.Column(db.DateTime, nullable=False, index=True)
    end_date = db.Column(db.DateTime)
    location = db.Column(db.String)
    is_virtual = db.Column(db.Boolean, default=False)
    url = db.Column(db.String)
    registration_url = db.Column(db.String)
    organizer = db.Column(db.String)
    source = db.Column(db.String)
    image_url = db.Column(db.String)
    
    # ESG categorization
    is_environmental = db.Column(db.Boolean, default=False)
    is_social = db.Column(db.Boolean, default=False)
    is_governance = db.Column(db.Boolean, default=False)
    
    # Additional metadata
    categories = db.Column(db.String)  # Comma-separated list of categories
    tags = db.Column(db.String)  # Comma-separated list of tags
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Event {self.title}>'
    
    @property
    def is_upcoming(self):
        """Check if the event is upcoming"""
        return self.start_date > datetime.utcnow()
    
    @property
    def is_ongoing(self):
        """Check if the event is currently ongoing"""
        now = datetime.utcnow()
        if self.end_date:
            return self.start_date <= now <= self.end_date
        return self.start_date.date() == now.date()
    
    @property
    def esg_categories(self):
        """Get the ESG categories as a list"""
        categories = []
        if self.is_environmental:
            categories.append('Environmental')
        if self.is_social:
            categories.append('Social')
        if self.is_governance:
            categories.append('Governance')
        return categories
    
    def to_dict(self):
        """Convert event to dictionary for API responses"""
        return {
            'id': self.id,
            'title': self.title,
            'summary': self.event_summary,  # Use event_summary for the API
            'description': self.description,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'location': self.location,
            'is_virtual': self.is_virtual,
            'url': self.url,
            'registration_url': self.registration_url,
            'organizer': self.organizer,
            'source': self.source,
            'image_url': self.image_url,
            'is_upcoming': self.is_upcoming,
            'is_ongoing': self.is_ongoing,
            'esg_categories': self.esg_categories,
            'categories': self.categories.split(',') if self.categories else [],
            'tags': self.tags.split(',') if self.tags else []
        } 
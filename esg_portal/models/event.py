"""
Event model for ESG-related events
"""
from datetime import datetime
from esg_portal import db

class Event(db.Model):
    """Model for ESG-related events"""
    __tablename__ = 'events'
    
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.String, unique=True, index=True)
    event_name = db.Column(db.String, nullable=False)
    event_url = db.Column(db.String)
    start_date = db.Column(db.Date, index=True)
    end_date = db.Column(db.Date)
    start_time = db.Column(db.String)
    end_time = db.Column(db.String)
    timezone = db.Column(db.String)
    image_url = db.Column(db.String)
    ticket_price = db.Column(db.String)
    tickets_url = db.Column(db.String)
    venue_name = db.Column(db.String)
    venue_address = db.Column(db.String)
    organizer_name = db.Column(db.String)
    organizer_url = db.Column(db.String)
    summary = db.Column(db.Text)
    tags = db.Column(db.String)
    source = db.Column(db.String)
    month = db.Column(db.String)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    @property
    def is_upcoming(self):
        """Check if the event is upcoming"""
        if not self.start_date:
            return False
        return self.start_date >= datetime.now().date()
    
    @property
    def is_ongoing(self):
        """Check if the event is currently ongoing"""
        now = datetime.now().date()
        if not self.start_date:
            return False
        if self.end_date:
            return self.start_date <= now <= self.end_date
        return self.start_date == now
    
    @property
    def esg_categories(self):
        """Get the ESG categories as a list based on tags"""
        categories = []
        if not self.tags:
            return categories
            
        tags_lower = self.tags.lower()
        if any(keyword in tags_lower for keyword in ['environment', 'climate', 'sustainable', 'green', 'esg']):
            categories.append('Environmental')
        if any(keyword in tags_lower for keyword in ['social', 'community', 'diversity', 'inclusion', 'esg']):
            categories.append('Social')
        if any(keyword in tags_lower for keyword in ['governance', 'corporate', 'compliance', 'board', 'esg']):
            categories.append('Governance')
        return categories
        
    @property
    def title(self):
        """Alias for event_name to maintain compatibility"""
        return self.event_name
        
    @property
    def url(self):
        """Alias for event_url to maintain compatibility"""
        return self.event_url
        
    @property
    def event_summary(self):
        """Alias for summary to maintain compatibility"""
        return self.summary
        
    @property
    def location(self):
        """Combine venue name and address"""
        if self.venue_name and self.venue_address:
            return f"{self.venue_name}, {self.venue_address}"
        return self.venue_name or self.venue_address or ""
        
    @property
    def is_virtual(self):
        """Check if event is virtual based on venue name"""
        if not self.venue_name:
            return False
        return 'virtual' in self.venue_name.lower() or 'online' in self.venue_name.lower()
        
    @property
    def organizer(self):
        """Alias for organizer_name to maintain compatibility"""
        return self.organizer_name
        
    @property
    def registration_url(self):
        """Alias for tickets_url to maintain compatibility"""
        return self.tickets_url
    
    def __repr__(self):
        return f'<Event {self.event_name}>'
    
    def to_dict(self):
        """Convert event to dictionary for API responses"""
        return {
            'id': self.id,
            'event_id': self.event_id,
            'title': self.title,
            'summary': self.summary,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'timezone': self.timezone,
            'location': self.location,
            'venue_name': self.venue_name,
            'venue_address': self.venue_address,
            'is_virtual': self.is_virtual,
            'url': self.url,
            'registration_url': self.registration_url,
            'organizer': self.organizer,
            'organizer_url': self.organizer_url,
            'source': self.source,
            'image_url': self.image_url,
            'ticket_price': self.ticket_price,
            'is_upcoming': self.is_upcoming,
            'is_ongoing': self.is_ongoing,
            'esg_categories': self.esg_categories,
            'tags': self.tags.split(',') if self.tags else [],
            'month': self.month
        }
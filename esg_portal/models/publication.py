"""
Publication model for ESG-related publications
"""
from datetime import datetime
from esg_portal import db

class Publication(db.Model):
    """Model for ESG-related publications"""
    __tablename__ = 'publications'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, nullable=False)
    summary = db.Column(db.Text)
    published_date = db.Column(db.Date, nullable=True, index=True)
    source = db.Column(db.String, nullable=True)
    link = db.Column(db.String, unique=True, nullable=False)
    image_url = db.Column(db.String)
    
    # These fields might not exist in the database, but we'll keep them in the model
    # and handle them in the routes
    published = db.Column(db.Date, nullable=True)  # Alias for published_date for compatibility
    
    # Publication details
    authors = db.Column(db.String(512))  # Comma-separated list of authors
    publisher = db.Column(db.String(256))
    publication_type = db.Column(db.String(64))  # e.g., Report, Whitepaper, Article
    
    # ESG categorization
    is_environmental = db.Column(db.Boolean, default=False)
    is_social = db.Column(db.Boolean, default=False)
    is_governance = db.Column(db.Boolean, default=False)
    
    # Additional metadata
    categories = db.Column(db.String(256))  # Comma-separated list of categories
    tags = db.Column(db.String(256))  # Comma-separated list of tags
    companies_mentioned = db.Column(db.String(512))  # Comma-separated list of companies
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Publication {self.title}>'
    
    @property
    def description(self):
        """Alias for summary to maintain compatibility with templates"""
        return self.summary
    
    @property
    def esg_categories(self):
        """Get the ESG categories as a list - placeholder for compatibility"""
        return []
    
    def to_dict(self):
        """Convert publication to dictionary for API responses"""
        return {
            'id': self.id,
            'title': self.title,
            'summary': self.summary,
            'description': self.summary,  # Use summary as description
            'published_date': self.published_date.isoformat() if self.published_date else None,
            'source': self.source,
            'link': self.link,
            'image_url': self.image_url,
            'authors': self.authors.split(',') if self.authors else [],
            'publisher': self.publisher,
            'publication_type': self.publication_type,
            'esg_categories': self.esg_categories,
            'categories': self.categories.split(',') if self.categories else [],
            'tags': self.tags.split(',') if self.tags else [],
            'companies_mentioned': self.companies_mentioned.split(',') if self.companies_mentioned else []
        } 
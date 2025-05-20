"""
Article model for ESG news articles
"""
from datetime import datetime
from esg_portal import db

class Article(db.Model):
    """Model for ESG news articles"""
    __tablename__ = 'articles'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(256), nullable=False)
    summary = db.Column(db.Text, nullable=False)
    content = db.Column(db.Text)
    published_date = db.Column(db.Date, nullable=True, index=True)
    source = db.Column(db.String(128), nullable=True, index=True)
    link = db.Column(db.String(512), unique=True, nullable=False)
    image_url = db.Column(db.String(512))
    matched_keywords = db.Column(db.String(256))
    
    # ESG categorization
    environmental_score = db.Column(db.Float)
    social_score = db.Column(db.Float)
    governance_score = db.Column(db.Float)
    
    # Additional metadata
    categories = db.Column(db.String(256))  # Comma-separated list of categories
    tags = db.Column(db.String(256))  # Comma-separated list of tags
    companies_mentioned = db.Column(db.String(512))  # Comma-separated list of companies
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Article {self.title}>'
    
    @property
    def esg_score(self):
        """Calculate the overall ESG score"""
        scores = [s for s in [self.environmental_score, self.social_score, self.governance_score] if s is not None]
        if not scores:
            return None
        return sum(scores) / len(scores)
    
    def to_dict(self):
        """Convert article to dictionary for API responses"""
        return {
            'id': self.id,
            'title': self.title,
            'summary': self.summary,
            'published_date': self.published_date.isoformat() if self.published_date else None,
            'source': self.source,
            'link': self.link,
            'image_url': self.image_url,
            'matched_keywords': self.matched_keywords.split(',') if self.matched_keywords else [],
            'environmental_score': self.environmental_score,
            'social_score': self.social_score,
            'governance_score': self.governance_score,
            'esg_score': self.esg_score,
            'categories': self.categories.split(',') if self.categories else [],
            'tags': self.tags.split(',') if self.tags else [],
            'companies_mentioned': self.companies_mentioned.split(',') if self.companies_mentioned else []
        }
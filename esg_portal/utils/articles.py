"""
Utility functions for handling articles data from the database
"""
from datetime import datetime, date
from esg_portal.utils import get_db_connection
from psycopg2.extras import RealDictCursor
import psycopg2.extras
from esg_portal.utils.cache import cache_result

@cache_result(ttl=300)  # Cache for 5 minutes
def get_latest_articles(limit=5):
    """Get the latest articles from the database"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        SELECT id, title, published, summary, link, source, matched_keywords 
        FROM esg_articles 
        WHERE published IS NOT NULL 
        ORDER BY published DESC 
        LIMIT %s
    """, (limit,))
    
    articles = cur.fetchall()
    conn.close()
    
    return articles

@cache_result(ttl=300)  # Cache for 5 minutes
def get_articles_by_date(filter_date=None, source=None):
    """Get articles by date and optionally by source"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    query = "SELECT id, title, published, summary, link, source, matched_keywords FROM esg_articles WHERE published IS NOT NULL"
    params = []
    
    if filter_date:
        query += " AND published = %s"
        params.append(filter_date)
    else:
        query += " AND published = %s"
        params.append(date.today())
    
    if source:
        query += " AND source = %s"
        params.append(source)
    
    query += " ORDER BY published DESC"
    
    cur.execute(query, params)
    articles = cur.fetchall()
    conn.close()
    
    return articles

@cache_result(ttl=600)  # Cache for 10 minutes
def get_article_by_id(id):
    """Get an article by ID from the database"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        SELECT id, title, published, summary, link, source, matched_keywords 
        FROM esg_articles 
        WHERE id = %s
    """, (id,))
    
    article = cur.fetchone()
    conn.close()
    
    return article

@cache_result(ttl=3600)  # Cache for 1 hour
def get_distinct_sources():
    """Get distinct article sources from the database"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT DISTINCT source 
        FROM esg_articles 
        WHERE source IS NOT NULL
    """)
    
    sources = [row[0] for row in cur.fetchall()]
    conn.close()
    
    return sources

def convert_to_article_objects(articles_data):
    """Convert article data to Article-like objects for template compatibility"""
    articles = []
    
    for art in articles_data:
        # Create a simple object with the same attributes as the Article model
        article = type('Article', (), {
            'id': art.get('id', ''),
            'title': art.get('title', ''),
            'summary': art.get('summary', ''),
            'published_date': art.get('published'),
            'source': art.get('source', ''),
            'link': art.get('link', ''),
            'matched_keywords': art.get('matched_keywords', ''),
            'esg_categories': [],  # Empty list for ESG categories
            'to_dict': lambda self=None: {
                'id': art.get('id', ''),
                'title': art.get('title', ''),
                'summary': art.get('summary', ''),
                'published_date': art.get('published').isoformat() if art.get('published') else None,
                'source': art.get('source', ''),
                'link': art.get('link', ''),
                'matched_keywords': art.get('matched_keywords', '').split(',') if art.get('matched_keywords') else []
            }
        })
        
        articles.append(article)
    
    return articles

@cache_result(ttl=600)  # Cache for 10 minutes
def get_articles_by_ids(article_ids):
    """Get articles by their IDs"""
    if not article_ids:
        return []
    
    # Convert to list if it's not already
    if not isinstance(article_ids, list):
        article_ids = [article_ids]
    
    # Create placeholders for the SQL query
    placeholders = ', '.join(['%s'] * len(article_ids))
    
    # Build the SQL query - changed to use esg_articles table to match other functions
    query = f"""
        SELECT id, title, published, summary, link, source, matched_keywords 
        FROM esg_articles
        WHERE id IN ({placeholders})
    """
    
    # Execute the query
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute(query, article_ids)
    articles = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return articles
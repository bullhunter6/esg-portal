"""
Utility functions for handling publications data from the database
"""
from datetime import datetime
from esg_portal.utils import get_db_connection
from psycopg2.extras import RealDictCursor
import psycopg2

def get_paginated_publications(page, per_page, search=None):
    """Get paginated publications from the database"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    offset = (page - 1) * per_page
    
    query = "SELECT id, image_url, title, summary, link, source, published FROM publications"
    
    if search:
        search_query = f"%{search.lower()}%"
        query += " WHERE LOWER(title) LIKE %s OR LOWER(summary) LIKE %s OR LOWER(source) LIKE %s"
        cur.execute(query + " ORDER BY published DESC LIMIT %s OFFSET %s", 
                   (search_query, search_query, search_query, per_page, offset))
    else:
        cur.execute(query + " ORDER BY published DESC LIMIT %s OFFSET %s", 
                   (per_page, offset))
    
    publications = cur.fetchall()
    
    # Get total count for pagination
    if search:
        cur.execute("SELECT COUNT(*) FROM publications WHERE LOWER(title) LIKE %s OR LOWER(summary) LIKE %s OR LOWER(source) LIKE %s", 
                   (search_query, search_query, search_query))
    else:
        cur.execute("SELECT COUNT(*) FROM publications")
    
    total_publications = cur.fetchone()['count']
    conn.close()
    
    return publications, total_publications

def get_latest_publications(limit=3):
    """Get the latest publications from the database"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("SELECT id, image_url, title, summary, link, source, published FROM publications ORDER BY published DESC LIMIT %s", 
               (limit,))
    
    publications = cur.fetchall()
    conn.close()
    
    return publications

def get_publication_by_id(id):
    """Get a publication by ID from the database"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("SELECT id, image_url, title, summary, link, source, published FROM publications WHERE id = %s", 
               (id,))
    
    publication = cur.fetchone()
    conn.close()
    
    return publication

def convert_to_publication_objects(publications_data):
    """Convert publication data to Publication-like objects for template compatibility"""
    publications = []
    
    for pub in publications_data:
        # Create a simple object with the same attributes as the Publication model
        publication = type('Publication', (), {
            'id': pub.get('id', ''),
            'title': pub.get('title', ''),
            'summary': pub.get('summary', ''),
            'description': pub.get('summary', ''),  # Use summary as description
            'published_date': pub.get('published'),
            'source': pub.get('source', ''),
            'link': pub.get('link', ''),
            'image_url': pub.get('image_url', ''),
            'esg_categories': [],  # Empty list for ESG categories
            'to_dict': lambda self=None: {
                'id': pub.get('id', ''),
                'title': pub.get('title', ''),
                'summary': pub.get('summary', ''),
                'description': pub.get('summary', ''),
                'published_date': pub.get('published').isoformat() if pub.get('published') else None,
                'source': pub.get('source', ''),
                'link': pub.get('link', ''),
                'image_url': pub.get('image_url', '')
            }
        })
        
        publications.append(publication)
    
    return publications

def get_publications_by_ids(publication_ids):
    """Get publications by their IDs"""
    if not publication_ids:
        return []
    
    # Convert to list if it's not already
    if not isinstance(publication_ids, list):
        publication_ids = [publication_ids]
    
    # Create placeholders for the SQL query
    placeholders = ', '.join(['%s'] * len(publication_ids))
    
    # Build the SQL query
    query = f"""
        SELECT * FROM publications
        WHERE id IN ({placeholders})
        ORDER BY published DESC
    """
    
    # Execute the query
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute(query, publication_ids)
    publications = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return publications 
"""
API routes for RESTful endpoints
"""
from datetime import datetime
from flask import jsonify, request, current_app
from sqlalchemy import desc, or_
from flask_login import login_required, current_user

from esg_portal.api import bp
from esg_portal.models.article import Article
from esg_portal.models.event import Event
from esg_portal.models.publication import Publication
from esg_portal import db
from esg_portal.models.like import Like

@bp.route('/articles')
def get_articles():
    """Get articles with optional filtering"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # Base query
    query = Article.query
    
    # Apply filters
    filter_date = request.args.get('date')
    if filter_date:
        try:
            filter_date = datetime.strptime(filter_date, '%Y-%m-%d').date()
            query = query.filter(Article.published_date == filter_date)
        except ValueError:
            pass
    
    filter_source = request.args.get('source')
    if filter_source:
        query = query.filter(Article.source == filter_source)
    
    search_term = request.args.get('search')
    if search_term:
        search_term = f"%{search_term}%"
        query = query.filter(
            or_(
                Article.title.ilike(search_term),
                Article.summary.ilike(search_term),
                Article.matched_keywords.ilike(search_term)
            )
        )
    
    # Paginate results
    pagination = query.order_by(desc(Article.published_date)).paginate(page=page, per_page=per_page)
    
    # Format response
    return jsonify({
        'articles': [article.to_dict() for article in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'page': page,
        'per_page': per_page
    })

@bp.route('/articles/<int:id>')
def get_article(id):
    """Get a specific article by ID"""
    article = Article.query.get_or_404(id)
    return jsonify(article.to_dict())

@bp.route('/events')
def get_events():
    """Get events with optional filtering"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # Filter option (upcoming, past, today)
    filter_option = request.args.get('option', 'upcoming')
    
    # Base query
    query = Event.query
    
    # Apply filters
    now = datetime.utcnow()
    
    if filter_option == 'upcoming':
        query = query.filter(Event.start_date >= now)
    elif filter_option == 'past':
        query = query.filter(Event.start_date < now)
    elif filter_option == 'today':
        query = query.filter(Event.start_date.between(
            datetime(now.year, now.month, now.day, 0, 0, 0),
            datetime(now.year, now.month, now.day, 23, 59, 59)
        ))
    
    # ESG category filter
    esg_filter = request.args.get('esg')
    if esg_filter == 'environmental':
        query = query.filter(Event.is_environmental == True)
    elif esg_filter == 'social':
        query = query.filter(Event.is_social == True)
    elif esg_filter == 'governance':
        query = query.filter(Event.is_governance == True)
    
    # Search term
    search_term = request.args.get('search')
    if search_term:
        search_term = f"%{search_term}%"
        query = query.filter(
            or_(
                Event.title.ilike(search_term),
                Event.summary.ilike(search_term),
                Event.description.ilike(search_term),
                Event.location.ilike(search_term),
                Event.organizer.ilike(search_term)
            )
        )
    
    # Sort order
    if filter_option == 'past':
        pagination = query.order_by(desc(Event.start_date)).paginate(page=page, per_page=per_page)
    else:
        pagination = query.order_by(Event.start_date).paginate(page=page, per_page=per_page)
    
    # Format response
    return jsonify({
        'events': [event.to_dict() for event in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'page': page,
        'per_page': per_page
    })

@bp.route('/events/<int:id>')
def get_event(id):
    """Get a specific event by ID"""
    event = Event.query.get_or_404(id)
    return jsonify(event.to_dict())

@bp.route('/publications')
def get_publications():
    """Get publications with optional filtering"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # Base query
    query = Publication.query
    
    # Apply filters
    filter_type = request.args.get('type')
    if filter_type:
        query = query.filter(Publication.publication_type == filter_type)
    
    # ESG category filter
    esg_filter = request.args.get('esg')
    if esg_filter == 'environmental':
        query = query.filter(Publication.is_environmental == True)
    elif esg_filter == 'social':
        query = query.filter(Publication.is_social == True)
    elif esg_filter == 'governance':
        query = query.filter(Publication.is_governance == True)
    
    # Search term
    search_term = request.args.get('search')
    if search_term:
        search_term = f"%{search_term}%"
        query = query.filter(
            or_(
                Publication.title.ilike(search_term),
                Publication.summary.ilike(search_term),
                Publication.description.ilike(search_term),
                Publication.authors.ilike(search_term),
                Publication.publisher.ilike(search_term)
            )
        )
    
    # Paginate results
    pagination = query.order_by(desc(Publication.published_date)).paginate(page=page, per_page=per_page)
    
    # Format response
    return jsonify({
        'publications': [publication.to_dict() for publication in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'page': page,
        'per_page': per_page
    })

@bp.route('/publications/<int:id>')
def get_publication(id):
    """Get a specific publication by ID"""
    publication = Publication.query.get_or_404(id)
    return jsonify(publication.to_dict())

@bp.route('/stats')
def get_stats():
    """Get general statistics about the portal"""
    # Count articles by source
    article_sources = db.session.query(
        Article.source, db.func.count(Article.id)
    ).group_by(Article.source).all()
    
    # Count events by ESG category
    environmental_events = Event.query.filter(Event.is_environmental == True).count()
    social_events = Event.query.filter(Event.is_social == True).count()
    governance_events = Event.query.filter(Event.is_governance == True).count()
    
    # Count publications by type
    publication_types = db.session.query(
        Publication.publication_type, db.func.count(Publication.id)
    ).group_by(Publication.publication_type).all()
    
    # Format response
    return jsonify({
        'articles': {
            'total': Article.query.count(),
            'by_source': {source: count for source, count in article_sources if source}
        },
        'events': {
            'total': Event.query.count(),
            'upcoming': Event.query.filter(Event.start_date >= datetime.utcnow()).count(),
            'by_category': {
                'environmental': environmental_events,
                'social': social_events,
                'governance': governance_events
            }
        },
        'publications': {
            'total': Publication.query.count(),
            'by_type': {pub_type: count for pub_type, count in publication_types if pub_type}
        }
    })

@bp.route('/like/<content_type>/<path:content_id>', methods=['POST'])
@login_required
def toggle_like(content_type, content_id):
    """Toggle like status for a content item"""
    # Validate content type
    if content_type not in ['article', 'event', 'publication']:
        return jsonify({'error': 'Invalid content type'}), 400
    
    try:
        # For events with string IDs, use a hash function
        # For articles and publications, use the integer ID
        if content_type == 'event' and not content_id.isdigit():
            # Create a consistent integer hash from the string ID
            # This avoids modifying your database schema
            numeric_id = abs(hash(content_id)) % (10 ** 9)  # Limit to 9 digits
        else:
            # For numeric IDs, convert to integer
            numeric_id = int(content_id)
        
        # Toggle like with the numeric ID
        is_liked = Like.toggle_like(current_user.id, content_type, numeric_id)
        
        # Get updated like count
        like_count = Like.get_content_likes_count(content_type, numeric_id)
        
        return jsonify({
            'success': True,
            'is_liked': is_liked,
            'like_count': like_count
        })
    except Exception as e:
        current_app.logger.error(f"Error toggling like: {e}")
        return jsonify({'error': 'Failed to process like'}), 500

@bp.route('/likes/status', methods=['GET'])
@login_required
def get_like_status():
    """Get like status for multiple content items"""
    content_items = request.args.get('items', '')
    if not content_items:
        return jsonify({'error': 'No content items specified'}), 400
    
    try:
        # Parse content items (format: "article:1,event:2,publication:3")
        items_list = content_items.split(',')
        result = {}
        
        # Process items and convert IDs as needed
        processed_items = {}
        for item in items_list:
            try:
                content_type, content_id = item.split(':')
                
                if content_type in ['article', 'event', 'publication']:
                    # For events with string IDs, use a hash function
                    # For articles and publications, use the integer ID
                    if content_type == 'event' and not content_id.isdigit():
                        numeric_id = abs(hash(content_id)) % (10 ** 9)
                    else:
                        numeric_id = int(content_id)
                    
                    # Store the mapping from original item to numeric ID
                    processed_items[item] = (content_type, numeric_id)
            except (ValueError, TypeError):
                # Skip invalid items
                continue
        
        # Get like status for all processed items
        for item, (content_type, numeric_id) in processed_items.items():
            # Check if user has liked this item
            is_liked = Like.is_liked(current_user.id, content_type, numeric_id)
            
            # Get total like count
            like_count = Like.get_content_likes_count(content_type, numeric_id)
            
            # Store result with original item key
            result[item] = {
                'is_liked': is_liked,
                'like_count': like_count
            }
        
        return jsonify({
            'success': True,
            'items': result
        })
    except Exception as e:
        current_app.logger.error(f"Error getting like status: {e}")
        return jsonify({'error': 'Failed to get like status'}), 500

@bp.route('/likes/user', methods=['GET'])
@login_required
def get_user_likes():
    """Get all likes for the current user"""
    content_type = request.args.get('type')
    
    try:
        likes = Like.get_user_likes(current_user.id, content_type)
        
        return jsonify({
            'success': True,
            'likes': [
                {
                    'content_type': like.content_type,
                    'content_id': like.content_id,
                    'created_at': like.created_at.isoformat()
                }
                for like in likes
            ]
        })
    except Exception as e:
        current_app.logger.error(f"Error getting user likes: {e}")
        return jsonify({'error': 'Failed to get user likes'}), 500 
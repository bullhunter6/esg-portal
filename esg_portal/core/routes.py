"""
Core routes for the main application functionality
"""
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from sqlalchemy import desc, or_

from esg_portal.core import bp
from esg_portal.models.article import Article  # Keep for type hints
from esg_portal.models.event import Event  # Keep for type hints
from esg_portal.models.publication import Publication  # Keep for type hints
from esg_portal import db
from esg_portal.utils.events import load_events_data, filter_events, search_events, get_event_by_id, get_upcoming_events
from esg_portal.utils.publications import get_latest_publications, get_paginated_publications, get_publication_by_id, convert_to_publication_objects
from esg_portal.utils.articles import get_latest_articles, get_articles_by_date, get_article_by_id, get_distinct_sources, convert_to_article_objects
from esg_portal.utils.logging_utils import log_user_activity, log_error

@bp.route('/')
def index():
    """Home page with latest articles, events, and publications"""
    # Get latest articles from the database
    try:
        articles_data = get_latest_articles(5)
        latest_articles = convert_to_article_objects(articles_data)
    except Exception as e:
        current_app.logger.error(f"Error loading articles: {e}")
        latest_articles = []
    
    # Get upcoming events from CSV
    try:
        upcoming_events = get_upcoming_events(3)
    except Exception as e:
        current_app.logger.error(f"Error loading events: {e}")
        upcoming_events = []
    
    # Get latest publications from the database
    try:
        publications_data = get_latest_publications(3)
        latest_publications = convert_to_publication_objects(publications_data)
    except Exception as e:
        current_app.logger.error(f"Error loading publications: {e}")
        latest_publications = []
    
    return render_template('core/index.html', 
                          articles=latest_articles,
                          events=upcoming_events,
                          publications=latest_publications,
                          now=datetime.now())

@bp.route('/articles')
@login_required
def articles():
    """List all articles with filtering options"""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Apply filters
    filter_date_str = request.args.get('date', '').strip()
    filter_date = None
    if filter_date_str:
        try:
            filter_date = datetime.strptime(filter_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    
    filter_source = request.args.get('source', '').strip()
    
    # Get articles from the database
    try:
        articles_data = get_articles_by_date(filter_date, filter_source)
        articles_list = convert_to_article_objects(articles_data)
        
        # Manual pagination
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        articles_page = articles_list[start_idx:end_idx]
        
        # Create a pagination object for template compatibility
        class Pagination:
            def __init__(self, items, page, per_page, total):
                self.items = items
                self.page = page
                self.per_page = per_page
                self.total = total
                self.pages = (total + per_page - 1) // per_page
                
            def iter_pages(self, left_edge=2, left_current=2, right_current=5, right_edge=2):
                last = 0
                for num in range(1, self.pages + 1):
                    if num <= left_edge or \
                       (num > self.page - left_current - 1 and num < self.page + right_current) or \
                       num > self.pages - right_edge:
                        if last + 1 != num:
                            yield None
                        yield num
                        last = num
        
        pagination = Pagination(articles_page, page, per_page, len(articles_list))
        
        # Get distinct sources for filter dropdown
        sources = get_distinct_sources()
        
    except Exception as e:
        current_app.logger.error(f"Error processing articles: {e}")
        articles_page = []
        pagination = None
        sources = []
    
    return render_template('core/articles.html',
                          articles=articles_page,
                          pagination=pagination,
                          sources=sources,
                          filter_date=filter_date,
                          filter_source=filter_source,
                          now=datetime.now())

@bp.route('/events')
@login_required
def events():
    """List all events with filtering options"""
    page = request.args.get('page', 1, type=int)
    per_page = 9
    
    # Filter option (upcoming, past, today)
    filter_option = request.args.get('option', 'upcoming')
    
    # ESG category filter
    esg_filter = request.args.get('esg')
    
    # Search term
    search_term = request.args.get('search')
    
    try:
        # Load events from database
        all_events = load_events_data()
        
        # Apply filters
        filtered_events = filter_events(all_events, filter_option)
        
        # Apply search if provided
        if search_term:
            filtered_events = search_events(filtered_events, search_term)
        
        # Apply ESG filter if provided
        if esg_filter:
            filtered_events = [event for event in filtered_events if esg_filter.capitalize() in event.esg_categories]
        
        # Calculate total for pagination
        total_events = len(filtered_events)
        
        # Manual pagination
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        events_page = filtered_events[start_idx:end_idx]
        
        # Create a pagination object for template compatibility
        class Pagination:
            def __init__(self, items, page, per_page, total):
                self.items = items
                self.page = page
                self.per_page = per_page
                self.total = total
                self.pages = (total + per_page - 1) // per_page
                
            def iter_pages(self, left_edge=2, left_current=2, right_current=5, right_edge=2):
                last = 0
                for num in range(1, self.pages + 1):
                    if num <= left_edge or \
                       (num > self.page - left_current - 1 and num < self.page + right_current) or \
                       num > self.pages - right_edge:
                        if last + 1 != num:
                            yield None
                        yield num
                        last = num
        
        pagination = Pagination(events_page, page, per_page, total_events)
        
        # Count for filter badges
        current_date = datetime.now().date()
        upcoming_count = len([e for e in all_events if e.start_date and e.start_date >= current_date])
        past_count = len([e for e in all_events if e.start_date and e.start_date < current_date])
        
    except Exception as e:
        current_app.logger.error(f"Error processing events: {e}")
        events_page = []
        pagination = None
        upcoming_count = 0
        past_count = 0
    
    return render_template('core/events.html',
                          events=events_page,
                          pagination=pagination,
                          filter_option=filter_option,
                          esg_filter=esg_filter,
                          search_term=search_term,
                          upcoming_count=upcoming_count,
                          past_count=past_count,
                          now=datetime.now())

@bp.route('/publications')
@login_required
def publications():
    """List all publications with filtering options"""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Search term
    search_term = request.args.get('search', '')
    
    try:
        # Get publications from the database
        publications_data, total_publications = get_paginated_publications(page, per_page, search_term)
        
        # Convert to publication objects
        publications_list = convert_to_publication_objects(publications_data)
        
        # Create a pagination object for template compatibility
        class Pagination:
            def __init__(self, items, page, per_page, total):
                self.items = items
                self.page = page
                self.per_page = per_page
                self.total = total
                self.pages = (total + per_page - 1) // per_page
                
            def iter_pages(self, left_edge=2, left_current=2, right_current=5, right_edge=2):
                last = 0
                for num in range(1, self.pages + 1):
                    if num <= left_edge or \
                       (num > self.page - left_current - 1 and num < self.page + right_current) or \
                       num > self.pages - right_edge:
                        if last + 1 != num:
                            yield None
                        yield num
                        last = num
        
        pagination = Pagination(publications_list, page, per_page, total_publications)
        
    except Exception as e:
        current_app.logger.error(f"Error processing publications: {e}")
        publications_list = []
        pagination = None
    
    return render_template('core/publications.html',
                          publications=publications_list,
                          pagination=pagination,
                          search_term=search_term,
                          now=datetime.now())

@bp.route('/article/<int:id>')
@login_required
def article_detail(id):
    """Display a single article"""
    try:
        # Get article from the database
        article_data = get_article_by_id(id)
        if not article_data:
            flash('Article not found', 'danger')
            return redirect(url_for('core.articles'))
        
        article = convert_to_article_objects([article_data])[0]
        
        # Log article view
        user_id = current_user.id if current_user.is_authenticated else 'anonymous'
        log_user_activity(
            user_id=user_id,
            action="view_article",
            details={
                "article_id": id,
                "article_title": article.title,
                "article_source": article.source
            }
        )
        
        return render_template('core/article_detail.html', article=article)
    except Exception as e:
        log_error(e, user_id=current_user.id if current_user.is_authenticated else None,
                 additional_info={"article_id": id})
        flash('Error loading article', 'danger')
        return redirect(url_for('core.articles'))

@bp.route('/event/<path:id>')
@login_required
def event_detail(id):
    """Show event details"""
    try:
        # If the ID is 'nan' or empty, redirect to the events page
        if id == 'nan' or not id:
            flash('Invalid event ID', 'warning')
            return redirect(url_for('core.events'))
            
        # Get event from database by ID
        event = get_event_by_id(id)
        
        if not event:
            current_app.logger.error(f"Event not found with ID: {id}")
            flash('Event not found', 'warning')
            return redirect(url_for('core.events'))
        
    except Exception as e:
        log_error(e, user_id=current_user.id if current_user.is_authenticated else None,
                 additional_info={"event_id": id})
        flash('Error loading event details', 'danger')
        return redirect(url_for('core.events'))
    
    return render_template('core/event_detail.html', event=event, now=datetime.now())

@bp.route('/publication/<int:id>')
@login_required
def publication_detail(id):
    """Display a single publication"""
    try:
        # Get publication from the database
        publication_data = get_publication_by_id(id)
        if not publication_data:
            flash('Publication not found', 'danger')
            return redirect(url_for('core.publications'))
        
        publication = convert_to_publication_objects([publication_data])[0]
        
        # Log publication view
        user_id = current_user.id if current_user.is_authenticated else 'anonymous'
        log_user_activity(
            user_id=user_id,
            action="view_publication",
            details={
                "publication_id": id,
                "publication_title": publication.title,
                "publication_source": publication.source
            }
        )
        
        return render_template('core/publication_detail.html', publication=publication)
    except Exception as e:
        log_error(e, user_id=current_user.id if current_user.is_authenticated else None,
                 additional_info={"publication_id": id})
        flash('Error loading publication', 'danger')
        return redirect(url_for('core.publications'))

from esg_portal.utils.articles import get_articles_by_ids
from esg_portal.utils.publications import get_publications_by_ids

def get_events_by_ids(event_ids):
    """Get events by their IDs"""
    if not event_ids:
        return []
    
    # Convert to list if it's not already
    if not isinstance(event_ids, list):
        event_ids = [event_ids]
    
    # First try to find events by event_id
    events = Event.query.filter(Event.event_id.in_(event_ids)).all()
    
    # If no events found, try to find by database id
    if not events:
        # Try to convert string IDs to integers for database lookup
        numeric_ids = []
        for id_str in event_ids:
            try:
                if isinstance(id_str, str):
                    # Try to extract numeric part if it's a string with non-numeric characters
                    if not id_str.isdigit():
                        import re
                        match = re.search(r'\d+', id_str)
                        if match:
                            numeric_ids.append(int(match.group()))
                    else:
                        numeric_ids.append(int(id_str))
                elif isinstance(id_str, int):
                    numeric_ids.append(id_str)
            except (ValueError, TypeError):
                continue
        
        # If we have any numeric IDs, try to find events by database ID
        if numeric_ids:
            events = Event.query.filter(Event.id.in_(numeric_ids)).all()
    
    # If still no events found, try partial matching on event_id
    if not events:
        # Use OR conditions for each ID
        conditions = [Event.event_id.ilike(f"%{id_str}%") for id_str in event_ids if isinstance(id_str, str)]
        if conditions:
            events = Event.query.filter(or_(*conditions)).all()
    
    return events

@bp.route('/dashboard')
@login_required
def dashboard():
    """User dashboard with personalized content"""
    # Get user's preferred categories
    preferred_categories = []
    if current_user.preferred_categories:
        preferred_categories = current_user.preferred_categories.split(',')
    
    # Get latest articles
    try:
        articles_data = get_latest_articles(5)
        personalized_articles = convert_to_article_objects(articles_data)
    except Exception as e:
        current_app.logger.error(f"Error loading articles for dashboard: {e}")
        personalized_articles = []
    
    # Get upcoming events from database
    try:
        # Get upcoming events
        upcoming_events = get_upcoming_events(5)
        
        # If user has preferred categories, filter events by tags
        if preferred_categories and upcoming_events:
            filtered_events = []
            for event in upcoming_events:
                if event.tags:
                    # Check if any preferred category is in the event tags
                    if any(category.lower() in event.tags.lower() for category in preferred_categories):
                        filtered_events.append(event)
            upcoming_events = filtered_events[:3]
        
    except Exception as e:
        current_app.logger.error(f"Error loading events for dashboard: {e}")
        upcoming_events = []
    
    # Get user's liked content
    from esg_portal.models.like import Like
    
    try:
        # Get liked articles
        article_likes = Like.get_user_likes(current_user.id, 'article')
        
        # Extract content IDs as integers
        article_ids = [int(like.content_id) for like in article_likes]
        
        # Get article data and convert to objects
        liked_articles = []
        if article_ids:
            try:
                # Log the article IDs for debugging
                current_app.logger.info(f"Fetching articles with IDs: {article_ids}")
                
                # Get articles by IDs
                articles_data = get_articles_by_ids(article_ids[:5])
                
                # Log retrieved articles for debugging
                current_app.logger.info(f"Retrieved {len(articles_data)} articles")
                
                # Convert to article objects
                liked_articles = convert_to_article_objects(articles_data)
            except Exception as e:
                current_app.logger.error(f"Error retrieving liked articles: {e}")
        
        # Modified event likes retrieval section for dashboard route
        # Get liked events
        event_likes = Like.get_user_likes(current_user.id, 'event')
        liked_events = []

        if event_likes:
            try:
                # Get the liked event IDs
                liked_event_ids = [like.content_id for like in event_likes]
                current_app.logger.info(f"Event IDs from likes table: {liked_event_ids}")
                
                # Try to get events - simplified approach
                liked_events = get_events_by_ids(liked_event_ids)
                
                current_app.logger.info(f"Retrieved {len(liked_events)} events")
            except Exception as e:
                current_app.logger.error(f"Error retrieving liked events: {str(e)}", exc_info=True)
        
        # Get liked publications
        publication_likes = Like.get_user_likes(current_user.id, 'publication')
        
        # Extract content IDs as integers
        publication_ids = [int(like.content_id) for like in publication_likes]
        
        # Get publication data and convert to objects
        liked_publications = []
        if publication_ids:
            try:
                # Log the publication IDs for debugging
                current_app.logger.info(f"Fetching publications with IDs: {publication_ids}")
                
                # Get publications by IDs
                publications_data = get_publications_by_ids(publication_ids[:5])
                
                # Log retrieved publications for debugging
                current_app.logger.info(f"Retrieved {len(publications_data)} publications")
                
                # Convert to publication objects
                liked_publications = convert_to_publication_objects(publications_data)
            except Exception as e:
                current_app.logger.error(f"Error retrieving liked publications: {e}")
        
    except Exception as e:
        current_app.logger.error(f"Error loading liked content: {e}")
        liked_articles = []
        liked_events = []
        liked_publications = []
    
    # Get like statistics FOR CURRENT USER ONLY
    try:
        from sqlalchemy import func
        
        # Count likes by content type FOR THE CURRENT USER
        like_stats = db.session.query(
            Like.content_type,
            func.count(Like.id).label('count')
        ).filter_by(user_id=current_user.id).group_by(Like.content_type).all()
        
        # Convert to dictionary
        like_counts = {
            'article': 0,
            'event': 0,
            'publication': 0
        }
        for content_type, count in like_stats:
            like_counts[content_type] = count
        
    except Exception as e:
        current_app.logger.error(f"Error loading like statistics: {e}")
        like_counts = {
            'article': 0,
            'event': 0,
            'publication': 0
        }
    
    return render_template('core/dashboard.html',
                          articles=personalized_articles,
                          events=upcoming_events,
                          liked_articles=liked_articles,
                          liked_events=liked_events,
                          liked_publications=liked_publications,
                          like_counts=like_counts,
                          now=datetime.now())
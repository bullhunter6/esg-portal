"""
Utility functions for handling events data from database
"""
from datetime import datetime
from dateutil import parser as date_parser
from sqlalchemy import desc, or_

from esg_portal import db
from esg_portal.models.event import Event

def parse_date(date_str):
    """Parse date string to datetime object"""
    try:
        # Handle '25 - 26 February 2025' by extracting the first date
        if ' - ' in date_str:
            date_str = date_str.split(' - ')[0]
        
        # Handle times if present
        parsed_date = date_parser.parse(date_str, fuzzy=True)
    except (ValueError, TypeError):
        parsed_date = None
    return parsed_date

def load_events_data():
    """Load events data from database"""
    # Query all events from the database
    events = Event.query.all()
    return events

def filter_events(events, filter_option):
    """Filter events based on the filter option"""
    current_date = datetime.now().date()
    
    if filter_option == 'upcoming':
        return [event for event in events if event.start_date and event.start_date >= current_date]
    elif filter_option == 'past':
        return [event for event in events if event.start_date and event.start_date < current_date]
    elif filter_option == 'today':
        return [event for event in events if event.start_date and event.start_date == current_date]
    else:
        return events

def search_events(events, search_term):
    """Search events based on the search term"""
    if not search_term:
        return events
    
    search_term = search_term.lower()
    
    # Search in title, summary, location, and organizer
    filtered_events = []
    for event in events:
        if (search_term in event.title.lower() or 
            (event.summary and search_term in event.summary.lower()) or
            (event.location and search_term in event.location.lower()) or
            (event.organizer and search_term in event.organizer.lower()) or
            (event.tags and search_term in event.tags.lower())):
            filtered_events.append(event)
    
    return filtered_events

def get_events_by_ids(event_ids):
    """Get events by their IDs"""
    if not event_ids:
        return []
    
    # Convert to list if it's not already
    if not isinstance(event_ids, list):
        event_ids = [event_ids]
    
    # Query events by event_id
    events = Event.query.filter(Event.event_id.in_(event_ids)).all()
    
    return events

def get_upcoming_events(limit=5):
    """Get upcoming events"""
    current_date = datetime.now().date()
    
    # Query upcoming events
    upcoming_events = Event.query.filter(
        Event.start_date >= current_date
    ).order_by(Event.start_date).limit(limit).all()
    
    return upcoming_events

def get_past_events(limit=5):
    """Get past events"""
    current_date = datetime.now().date()
    
    # Query past events
    past_events = Event.query.filter(
        Event.start_date < current_date
    ).order_by(desc(Event.start_date)).limit(limit).all()
    
    return past_events

def get_event_by_id(event_id):
    """Get a single event by ID"""
    # First try exact match
    event = Event.query.filter(Event.event_id == event_id).first()
    
    # If not found, try case-insensitive match
    if not event:
        event = Event.query.filter(Event.event_id.ilike(f"%{event_id}%")).first()
    
    return event
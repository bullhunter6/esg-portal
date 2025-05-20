"""
Utility functions for handling events data from CSV
"""
import os
import pandas as pd
from datetime import datetime
from dateutil import parser as date_parser

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
    """Load events data from CSV file"""
    # Get the absolute path to the CSV file
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(base_dir, 'static', 'events.csv')
    
    # Load the CSV file
    events_df = pd.read_csv(csv_path)
    
    # Remove any extra whitespace from column names
    events_df.columns = [col.strip() for col in events_df.columns]
    
    # Create a unique ID for each event
    # First, check if 'Event ID' column exists
    if 'Event ID' in events_df.columns:
        # Create a new 'id' column, using Event ID if available, otherwise generate a new ID
        events_df['id'] = events_df.apply(
            lambda row: str(row['Event ID']) if pd.notna(row['Event ID']) and str(row['Event ID']).strip() 
            else f"event-{row.name}-{row['Event Name'].lower().replace(' ', '-')[:20]}", 
            axis=1
        )
    else:
        # If 'Event ID' doesn't exist, create a new 'id' column
        events_df['id'] = [f"event-{i}-{row['Event Name'].lower().replace(' ', '-')[:20]}" 
                          for i, (_, row) in enumerate(events_df.iterrows())]
    
    # Rename other columns for easier usage
    column_mapping = {
        'Event Name': 'title',
        'Event URL': 'url',
        'Start Date': 'start_date',
        'End Date': 'end_date',
        'Summary': 'event_summary',
        'Venue Name': 'location',
        'Organizer Name': 'organizer',
        'Image URL': 'image_url',
        'Tags': 'tags',
        'Source': 'source',
        'Tickets URL': 'registration_url'
    }
    
    # Only rename columns that actually exist in the DataFrame
    rename_dict = {k: v for k, v in column_mapping.items() if k in events_df.columns}
    events_df.rename(columns=rename_dict, inplace=True)
    
    # Convert date columns to datetime
    for date_col in ['start_date', 'end_date']:
        if date_col in events_df.columns:
            events_df[date_col] = events_df[date_col].apply(lambda x: parse_date(str(x)) if not pd.isna(x) else None)
    
    # Ensure event_summary is always a string
    if 'event_summary' in events_df.columns:
        events_df['event_summary'] = events_df['event_summary'].fillna('').astype(str)
    
    return events_df

def filter_events(events_df, filter_option):
    """Filter events based on the filter option"""
    current_date = datetime.now().date()
    
    if filter_option == 'upcoming':
        filtered_events_df = events_df[events_df['start_date'].dt.date >= current_date].sort_values(by='start_date')
    elif filter_option == 'past':
        filtered_events_df = events_df[events_df['start_date'].dt.date < current_date].sort_values(by='start_date', ascending=False)
    elif filter_option == 'today':
        filtered_events_df = events_df[events_df['start_date'].dt.date == current_date]
    else:
        filtered_events_df = events_df.sort_values(by='start_date')
    
    return filtered_events_df

def search_events(events_df, search_term):
    """Search events based on the search term"""
    if not search_term:
        return events_df
    
    search_term = search_term.lower()
    
    # Search in title, summary, location, and organizer
    mask = (
        events_df['title'].str.lower().str.contains(search_term, na=False) |
        events_df['event_summary'].str.lower().str.contains(search_term, na=False) |
        events_df['location'].str.lower().str.contains(search_term, na=False) |
        events_df['organizer'].str.lower().str.contains(search_term, na=False) |
        events_df['tags'].str.lower().str.contains(search_term, na=False)
    )
    
    return events_df[mask]

def convert_to_event_objects(events_df):
    """Convert DataFrame rows to Event-like objects for template compatibility"""
    events = []
    
    for idx, row in events_df.iterrows():
        # Handle missing end_date by using start_date as fallback
        end_date = row.get('end_date') if 'end_date' in row else None
        if pd.isna(end_date):
            end_date = row.get('start_date') if 'start_date' in row else None
        
        # Convert date strings to datetime objects if they're not already
        start_date = row.get('start_date') if 'start_date' in row else None
        if start_date and not isinstance(start_date, datetime):
            try:
                start_date = parse_date(str(start_date))
            except:
                start_date = None
                
        if end_date and not isinstance(end_date, datetime):
            try:
                end_date = parse_date(str(end_date))
            except:
                end_date = None
        
        # Ensure ID is valid - this should already be handled in load_events_data
        # but we'll add an extra check here just to be safe
        event_id = row.get('id', '')
        if pd.isna(event_id) or not str(event_id).strip():
            # Create a unique ID based on the index and title
            title = row.get('title', '') if 'title' in row else ''
            if pd.isna(title) or not title:
                title = f"event-{idx}"
            else:
                title = title.lower().replace(' ', '-')[:20]
            event_id = f"event-{idx}-{title}"
        
        # Create a simple object with the same attributes as the Event model
        event = type('Event', (), {
            'id': str(event_id),  # Ensure ID is always a string and never empty
            'title': row.get('title', '') if not pd.isna(row.get('title', '')) else f"Event {idx}",
            'event_summary': row.get('event_summary', '') if not pd.isna(row.get('event_summary', '')) else '',
            'description': row.get('event_summary', '') if not pd.isna(row.get('event_summary', '')) else '',
            'start_date': start_date,
            'end_date': end_date,
            'location': row.get('location', '') if not pd.isna(row.get('location', '')) else '',
            'is_virtual': 'virtual' in str(row.get('location', '')).lower() if not pd.isna(row.get('location', '')) else False,
            'url': row.get('url', '') if not pd.isna(row.get('url', '')) else '',
            'registration_url': row.get('registration_url', '') if not pd.isna(row.get('registration_url', '')) else row.get('url', '') if not pd.isna(row.get('url', '')) else '',
            'organizer': row.get('organizer', '') if not pd.isna(row.get('organizer', '')) else '',
            'source': row.get('source', '') if not pd.isna(row.get('source', '')) else '',
            'image_url': row.get('image_url', '') if not pd.isna(row.get('image_url', '')) else '',
            'tags': row.get('tags', '') if not pd.isna(row.get('tags', '')) else '',
            'esg_categories': []  # Empty list for ESG categories
        })
        
        # Add ESG categories based on tags
        tags_lower = str(row.get('tags', '')).lower()
        if any(keyword in tags_lower for keyword in ['environment', 'climate', 'sustainable', 'green', 'esg']):
            event.esg_categories.append('Environmental')
        if any(keyword in tags_lower for keyword in ['social', 'community', 'diversity', 'inclusion', 'esg']):
            event.esg_categories.append('Social')
        if any(keyword in tags_lower for keyword in ['governance', 'corporate', 'compliance', 'board', 'esg']):
            event.esg_categories.append('Governance')
        
        events.append(event)
    
    return events

def get_events_by_ids(event_ids):
    """Get events by their IDs"""
    if not event_ids:
        return []
    
    # Convert to list if it's not already
    if not isinstance(event_ids, list):
        event_ids = [event_ids]
    
    # Load all events
    events_df = load_events_data()
    
    # Filter events by ID
    filtered_df = events_df[events_df['id'].isin(event_ids)]
    
    # Convert to event objects
    return convert_to_event_objects(filtered_df)

def get_upcoming_events(limit=5):
    """Get upcoming events"""
    # Load all events
    events_df = load_events_data()
    
    # Filter for upcoming events
    filtered_df = filter_events(events_df, 'upcoming')
    
    # Limit the number of events
    limited_df = filtered_df.head(limit)
    
    # Convert to event objects
    return convert_to_event_objects(limited_df)
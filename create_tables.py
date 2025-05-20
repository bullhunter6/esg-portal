"""
Script to create all database tables from SQLAlchemy models
"""
from esg_portal import create_app, db
from esg_portal.models.file_upload import FileUpload

def create_tables():
    """Create all database tables"""
    app = create_app()
    with app.app_context():
        # Create all tables
        db.create_all()
        print("All database tables created successfully.")

if __name__ == "__main__":
    create_tables()

"""
ESG News Portal - A modern application for tracking ESG news, events, and publications
"""
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_caching import Cache
import logging


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import config classes
from esg_portal.config import config_classes

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
cache = Cache()

def create_app(test_config=None):
    """Create and configure the Flask application."""
    
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_classes["default"])

    if test_config:
        app.config.update(test_config)
    
    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        pass
    
    # Configure upload folder
    upload_folder = os.path.join(app.instance_path, 'uploads')
    os.makedirs(upload_folder, exist_ok=True)
    app.config['UPLOAD_FOLDER'] = upload_folder
    
    # Set up logging
    from esg_portal.utils.logging_utils import setup_logging
    setup_logging(app)
    
    # Initialize Flask-Executor for background tasks
    from esg_portal.utils.executor import init_app as init_executor
    init_executor(app)
    app.logger.info("Executor initialized")
    
    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    cache.init_app(app)
    
    # Add hasattr as a global function in templates
    @app.context_processor
    def utility_processor():
        return {
            'hasattr': hasattr
        }
    
    # Register blueprints
    from esg_portal.core import bp as core_bp
    app.register_blueprint(core_bp)
    
    from esg_portal.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    from esg_portal.api import bp as api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    
    from esg_portal.esg_scores import bp as esg_scores_bp
    app.register_blueprint(esg_scores_bp)
    
    # Register admin blueprint
    from esg_portal.admin import bp as admin_bp
    app.register_blueprint(admin_bp)
    
    # Add context processors
    @app.context_processor
    def inject_now():
        from datetime import datetime
        return {'now': datetime.now()}
    
    return app
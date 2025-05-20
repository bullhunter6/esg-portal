"""
Configuration settings for the ESG Portal application
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev_key_change_in_production')
    
    # SQLAlchemy configuration
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:finvizier2023@esgarticles.cf4iaa2amdt3.me-central-1.rds.amazonaws.com:5432/postgres'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Determine if Redis is available
    REDIS_AVAILABLE = os.environ.get('REDIS_AVAILABLE', 'false').lower() == 'true'
    
    # Celery configuration with fallback to SQLite database
    if REDIS_AVAILABLE:
        CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
        CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
        SOCKETIO_MESSAGE_QUEUE = os.environ.get('SOCKETIO_MESSAGE_QUEUE', 'redis://localhost:6379/0')
        
        # Cache configuration
        CACHE_TYPE = 'redis'
        CACHE_REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/1')
    else:
        # Use SQLite as a fallback
        CELERY_BROKER_URL = 'sqla+sqlite:///instance/celery-broker.sqlite'
        CELERY_RESULT_BACKEND = 'db+sqlite:///instance/celery-results.sqlite'
        SOCKETIO_MESSAGE_QUEUE = None
        
        # Cache configuration
        CACHE_TYPE = 'simple'
    
    CACHE_DEFAULT_TIMEOUT = 300
    
    # Upload folder
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'instance', 'uploads'))
    
    # SocketIO configuration
    SOCKETIO_SERVER_URL = os.environ.get('SOCKETIO_SERVER_URL', 'http://localhost:8000')
    
    # Logging configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_ECHO = True

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    
    # Use stronger security settings in production
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True

# Configuration dictionary
config_classes = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
} 
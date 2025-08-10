"""
Configuration for Railway deployment
Supports both SQLite (local) and PostgreSQL (Railway)
"""

import os
from datetime import timedelta

class Config:
    """Base configuration"""
    
    # Security
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production-xyz789'
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None
    
    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_SECURE = os.environ.get('RAILWAY_ENVIRONMENT') is not None
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Database configuration - auto-detect Railway PostgreSQL
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if DATABASE_URL:
        # Railway PostgreSQL
        # Fix for SQLAlchemy (replace postgres:// with postgresql://)
        if DATABASE_URL.startswith('postgres://'):
            DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
        print(f"[INFO] Using PostgreSQL database (Railway): {DATABASE_URL[:50]}...")
    else:
        # Local SQLite
        basedir = os.path.abspath(os.path.dirname(__file__))
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(basedir, "minutes_tracker.db")}'
        print("[INFO] Using SQLite database (Local)")
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True
    }
    
    # Application settings
    APP_NAME = 'WikiDesk'
    APP_VERSION = '2.0.0'
    
    # File upload settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'xlsx', 'xls', 'csv'}
    
    # Export settings
    EXPORT_FOLDER = os.path.join(os.path.dirname(__file__), 'exports')
    
    # Backup settings (local only)
    BACKUP_FOLDER = os.path.join(os.path.dirname(__file__), 'backups')
    BACKUP_ENABLED = os.environ.get('DATABASE_URL') is None  # Only for local SQLite
    
    # SocketIO settings
    SOCKETIO_ASYNC_MODE = 'threading'
    
    @staticmethod
    def init_app(app):
        """Initialize application"""
        # Create necessary directories
        for folder in [Config.UPLOAD_FOLDER, Config.EXPORT_FOLDER, Config.BACKUP_FOLDER]:
            os.makedirs(folder, exist_ok=True)

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    
    # Use environment variables in production
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(32).hex()
    
    # Security headers
    SEND_FILE_MAX_AGE_DEFAULT = 31536000  # 1 year
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Log to stdout in production
        import logging
        from logging import StreamHandler
        stream_handler = StreamHandler()
        stream_handler.setLevel(logging.INFO)
        app.logger.addHandler(stream_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('WikiDesk startup')

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

# Auto-select configuration based on environment
def get_config():
    """Get configuration based on environment"""
    if os.environ.get('RAILWAY_ENVIRONMENT'):
        return ProductionConfig
    return DevelopmentConfig
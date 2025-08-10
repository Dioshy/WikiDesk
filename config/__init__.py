"""
Configuration package for WikiDesk application
"""

import os
from pathlib import Path

# Ensure database is in correct location
def get_database_uri():
    """Get the correct database URI for WikiDesk"""
    # Check if environment variable is set (from run_simple.py)
    env_uri = os.environ.get('SQLALCHEMY_DATABASE_URI')
    if env_uri:
        return env_uri
    
    # Fallback to default WikiDesk shared location
    db_dir = Path.home() / "WikiDesk_Shared"
    db_dir.mkdir(exist_ok=True)
    db_path = db_dir / "minutes_tracker.db"
    return f'sqlite:///{str(db_path)}'

# Default configuration classes
class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'wikiDesk-secret-key-2024'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = get_database_uri()
    BACKUP_PATH = 'backups'
    EXPORT_PATH = 'exports' 
    WTF_CSRF_ENABLED = False

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or 'sqlite:///minutes_tracker.db'

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///minutes_tracker.db'

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
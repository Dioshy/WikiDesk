from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_socketio import SocketIO
from flask_migrate import Migrate
import os

# Try to import config, with fallback
try:
    from config import config
except ImportError:
    config = {
        'default': type('Config', (), {
            'SECRET_KEY': 'wikiDesk-secret-key-2024',
            'SQLALCHEMY_TRACK_MODIFICATIONS': False,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///minutes_tracker.db'
        })
    }

# Try to import deployment config, with fallback
try:
    from config.deployment import deployment_config
except ImportError:
    deployment_config = type('DeploymentConfig', (), {
        'get_database_url': lambda: None,
        'load_config': lambda: None
    })()

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
socketio = SocketIO(cors_allowed_origins="*", ping_timeout=60, ping_interval=25, async_mode='threading', logger=False, engineio_logger=False)

def create_app(config_class=None):
    app = Flask(__name__)
    
    # Use provided config class or auto-detect
    if config_class:
        app.config.from_object(config_class)
    else:
        # Check for Railway config first
        try:
            from config_railway import get_config
            app.config.from_object(get_config())
        except ImportError:
            # Fallback to deployment config
            deployment_db_url = deployment_config.get_database_url()
            if deployment_db_url:
                app.config['SQLALCHEMY_DATABASE_URI'] = deployment_db_url
                print(f"Using deployment database: {deployment_db_url}")
            else:
                config_name = os.environ.get('FLASK_ENV', 'default')
                app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(app, cors_allowed_origins="*", async_mode='threading')
    
    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.admin import admin_bp
    from app.routes.api import api_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Import models to ensure they're registered
    from app import models
    
    # Initialize real-time sync
    from app.realtime_sync import realtime_sync
    realtime_sync.init_app(app, socketio)
    
    # Initialize database manager
    from app.database_manager import db_manager
    
    # Create backup directory if it doesn't exist
    backup_path = app.config.get('BACKUP_PATH', 'backups')
    os.makedirs(backup_path, exist_ok=True)
    
    return app

@login_manager.user_loader
def load_user(user_id):
    from app.models.user import User
    return User.query.get(int(user_id))
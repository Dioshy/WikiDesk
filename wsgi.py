"""
WSGI entry point for Railway deployment
Forces PostgreSQL usage and proper production configuration
"""

import os
import sys
from pathlib import Path

# Force Railway environment variables
os.environ['RAILWAY_ENVIRONMENT'] = 'true'
os.environ['FLASK_ENV'] = 'production'

# Add the app directory to Python path
app_dir = Path(__file__).parent
sys.path.insert(0, str(app_dir))

print("[WSGI] Starting WikiDesk for Railway...")

# Force PostgreSQL detection
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    # Fix postgres:// to postgresql:// for SQLAlchemy
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
        os.environ['DATABASE_URL'] = DATABASE_URL
    print(f"[WSGI] PostgreSQL detected: {DATABASE_URL[:50]}...")
else:
    print("[WSGI] WARNING: No DATABASE_URL found!")

# Import after setting environment
from app import create_app, socketio, db
from app.models.user import User
from app.models.courtier import Courtier

# Create app with explicit Railway config
from config_railway import ProductionConfig
app = create_app(config_class=ProductionConfig)

def init_database():
    """Initialize database with default data"""
    with app.app_context():
        try:
            # Create all tables
            db.create_all()
            print("[WSGI] Tables created/verified")
            
            # Check if admin exists
            admin = User.query.filter_by(username='admin').first()
            if not admin:
                # Create admin user
                admin = User(
                    username='admin',
                    email='admin@wikidesk.local',
                    full_name='Administrateur',
                    password='admin123'
                )
                admin.role = 'admin'
                admin.is_active = True
                
                db.session.add(admin)
                db.session.commit()
                print("[WSGI] Admin user created (admin/admin123)")
            
            # Create demo user if not exists
            demo_user = User.query.filter_by(username='utilisateur').first()
            if not demo_user:
                demo_user = User(
                    username='utilisateur',
                    email='user@wikidesk.local',
                    full_name='Utilisateur Demo',
                    password='user123'
                )
                demo_user.role = 'user'
                demo_user.is_active = True
                
                db.session.add(demo_user)
                db.session.commit()
                print("[WSGI] Demo user created (utilisateur/user123)")
            
            # Add default courtiers if none exist
            if Courtier.query.count() == 0:
                default_courtiers = [
                    'AXA', 'Allianz', 'Generali', 'MAIF', 
                    'MACIF', 'MMA', 'Groupama', 'Crédit Agricole', 'Autres'
                ]
                
                for courtier_name in default_courtiers:
                    courtier = Courtier(name=courtier_name)
                    db.session.add(courtier)
                
                db.session.commit()
                print(f"[WSGI] {len(default_courtiers)} default courtiers added")
                
        except Exception as e:
            print(f"[WSGI] Database initialization error: {e}")

# Initialize database
init_database()

print("[WSGI] WikiDesk initialized successfully")

# For gunicorn
application = app

# Always run the server when this file is executed (Railway calls python wsgi.py)
port = int(os.environ.get('PORT', 5000))
print(f"[WSGI] Starting WikiDesk on port {port}")
print(f"[WSGI] Database: {'PostgreSQL (Railway)' if os.environ.get('DATABASE_URL') else 'SQLite (Local)'}")

# Force the app to start
socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)
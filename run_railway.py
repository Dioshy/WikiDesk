"""
Railway deployment entry point for WikiDesk
Auto-configures for PostgreSQL when DATABASE_URL is present
"""

import os
import sys
from pathlib import Path

# Add the app directory to Python path
app_dir = Path(__file__).parent
sys.path.insert(0, str(app_dir))

# Set configuration
os.environ['FLASK_APP'] = 'app'
os.environ['FLASK_ENV'] = 'production' if os.environ.get('RAILWAY_ENVIRONMENT') else 'development'

from app import create_app, socketio, db
from app.models.user import User
from app.models.courtier import Courtier
from config_railway import get_config

def init_database(app):
    """Initialize database with default data"""
    with app.app_context():
        # Create all tables
        db.create_all()
        print("[OK] Tables créées/vérifiées")
        
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
            print("[OK] Utilisateur admin créé (admin/admin123)")
        
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
            print("[OK] Utilisateur demo créé (utilisateur/user123)")
        
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
            print(f"[OK] {len(default_courtiers)} courtiers par défaut ajoutés")

def create_application():
    """Create and configure the application"""
    # Use Railway config
    app = create_app(config_class=get_config())
    
    # Initialize database
    init_database(app)
    
    return app

# Create app instance
app = create_application()

if __name__ == '__main__':
    # Get port from environment or default
    port = int(os.environ.get('PORT', 5000))
    
    # Check if running on Railway
    if os.environ.get('RAILWAY_ENVIRONMENT'):
        print(f"[INFO] Running on Railway (Production)")
        # Use gunicorn in production (Railway will handle this)
        socketio.run(app, host='0.0.0.0', port=port, debug=False)
    else:
        print(f"[INFO] Running locally (Development)")
        print(f"[INFO] Access at: http://localhost:{port}")
        socketio.run(app, host='0.0.0.0', port=port, debug=True)
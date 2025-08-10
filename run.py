#!/usr/bin/env python3
"""
Main entry point for WikiDesk - Railway compatible
Auto-configures for PostgreSQL when DATABASE_URL is present
"""

import os
import sys
from pathlib import Path

# Add the app directory to Python path
app_dir = Path(__file__).parent
sys.path.insert(0, str(app_dir))

# Set configuration for Railway
os.environ['FLASK_APP'] = 'app'
if os.environ.get('RAILWAY_ENVIRONMENT'):
    os.environ['FLASK_ENV'] = 'production'

from app import create_app, socketio, db
from app.models.user import User
from app.models.courtier import Courtier

# Auto-detect configuration
try:
    from config_railway import get_config
    app = create_app(config_class=get_config())
    print("[INFO] Using Railway configuration")
except ImportError:
    app = create_app()
    print("[INFO] Using default configuration")

def init_database():
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

@app.cli.command()
def init_db():
    """Initialize the database"""
    db.create_all()
    print("Database initialized!")

@app.cli.command()
def create_admin():
    """Create an admin user"""
    admin = User(
        username='admin',
        email='admin@company.com',
        full_name='System Administrator',
        password='admin123',
        role='admin'
    )
    db.session.add(admin)
    
    # Add some sample courtiers
    sample_courtiers = [
        Courtier('Allianz France', 'ALZ_001'),
        Courtier('AXA Assurances', 'AXA_001'),
        Courtier('Generali France', 'GEN_001'),
        Courtier('MAIF', 'MAIF_001'),
        Courtier('Groupama', 'GRP_001')
    ]
    
    for courtier in sample_courtiers:
        db.session.add(courtier)
    
    db.session.commit()
    print("Admin user created with username 'admin' and password 'admin123'")
    print("Sample courtiers added to database")

@app.shell_context_processor
def make_shell_context():
    return {
        'db': db, 
        'User': User, 
        'Entry': Entry, 
        'Courtier': Courtier
    }

if __name__ == '__main__':
    # Initialize database
    init_database()
    
    # Get port from environment
    port = int(os.environ.get('PORT', 5000))
    
    # Check if running on Railway
    if os.environ.get('RAILWAY_ENVIRONMENT') or os.environ.get('DATABASE_URL'):
        print(f"[INFO] Running on Railway (Production)")
        socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)
    else:
        print(f"[INFO] Running locally (Development)")
        print(f"[INFO] Access at: http://localhost:{port}")
        socketio.run(app, host='0.0.0.0', port=port, debug=True, allow_unsafe_werkzeug=True)
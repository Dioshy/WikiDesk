"""
Forced entry point for Railway - completely new file to trigger rebuild
"""

import os
import sys

# Force all Railway environment settings
os.environ['RAILWAY_ENVIRONMENT'] = 'production'
os.environ['FLASK_ENV'] = 'production'

print("=== WIKIDESK RAILWAY STARTUP ===")
print("Checking environment...")

# Debug all environment variables
DATABASE_URL = os.environ.get('DATABASE_URL')
print(f"DATABASE_URL found: {DATABASE_URL is not None}")

if DATABASE_URL:
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
        os.environ['DATABASE_URL'] = DATABASE_URL
    print(f"Using PostgreSQL: {DATABASE_URL[:60]}...")
else:
    # Look for Railway PostgreSQL variables
    pg_vars = {}
    for key, value in os.environ.items():
        if 'PG' in key.upper() or 'POSTGRES' in key.upper():
            pg_vars[key] = value
    
    if pg_vars:
        print("Found PostgreSQL variables:")
        for key, value in pg_vars.items():
            if 'PASSWORD' in key.upper():
                print(f"  {key}: ***HIDDEN***")
            else:
                print(f"  {key}: {value}")
    else:
        print("No PostgreSQL variables found!")

# Import and run
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app, socketio, db
from app.models.user import User
from app.models.courtier import Courtier

# Force Railway config
from config_railway import ProductionConfig
app = create_app(config_class=ProductionConfig)

print("\n=== DATABASE INITIALIZATION ===")
with app.app_context():
    try:
        db.create_all()
        print("✓ Tables created")
        
        # Create admin if not exists
        if not User.query.filter_by(username='admin').first():
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
            print("✓ Admin created: admin/admin123")
        
        # Create demo user
        if not User.query.filter_by(username='utilisateur').first():
            demo = User(
                username='utilisateur',
                email='user@wikidesk.local',
                full_name='Utilisateur Demo',
                password='user123'
            )
            demo.role = 'user'
            demo.is_active = True
            db.session.add(demo)
            db.session.commit()
            print("✓ Demo user created: utilisateur/user123")
        
        # Add courtiers
        if Courtier.query.count() == 0:
            courtiers = ['AXA', 'Allianz', 'Generali', 'MAIF', 'MACIF', 'MMA', 'Groupama', 'Crédit Agricole', 'Autres']
            for name in courtiers:
                db.session.add(Courtier(name=name))
            db.session.commit()
            print(f"✓ {len(courtiers)} courtiers created")
            
    except Exception as e:
        print(f"✗ Database error: {e}")

print("\n=== STARTING WIKIDESK ===")
port = int(os.environ.get('PORT', 8080))
print(f"Starting on port {port}")

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)
else:
    # For gunicorn
    application = app
"""
Main application entry point for WikiDesk
Handles both server and client modes based on configuration
"""
import os
import sys
import webbrowser
import time
import threading
from pathlib import Path

# Add the app directory to Python path
app_dir = Path(__file__).parent.parent
sys.path.insert(0, str(app_dir))

from app import create_app, socketio, db
from config.deployment import deployment_config
from app.database_manager import db_manager
from app.realtime_sync import realtime_sync

class WikiDeskLauncher:
    def __init__(self):
        self.app = None
        self.config = deployment_config.load_config()
        self.is_server_mode = deployment_config.is_server_mode()
        
    def initialize_database(self):
        """Initialize database tables"""
        try:
            with self.app.app_context():
                # Test database connection
                if not db_manager.test_connection():
                    print("❌ Cannot connect to database")
                    print("Please check your database configuration")
                    return False
                
                # Create tables if they don't exist
                db.create_all()
                
                # Create default admin user if none exists
                self.create_default_admin()
                
                print("✅ Database initialized successfully")
                return True
                
        except Exception as e:
            print(f"❌ Database initialization failed: {str(e)}")
            return False
    
    def create_default_admin(self):
        """Create default admin user if none exists"""
        from app.models.user import User
        
        admin_exists = User.query.filter_by(role='admin').first()
        if not admin_exists:
            admin_user = User(
                username='admin',
                email='admin@wikiDesk.local',
                full_name='Administrateur',
                password='admin123',
                role='admin'
            )
            db.session.add(admin_user)
            db.session.commit()
            print("✅ Default admin user created (username: admin, password: admin123)")
    
    def start_background_tasks(self):
        """Start background tasks for server mode"""
        if self.is_server_mode:
            # Start backup scheduler
            from app.utils.backup_scheduler import start_backup_scheduler
            backup_thread = threading.Thread(target=start_backup_scheduler, args=(self.app,))
            backup_thread.daemon = True
            backup_thread.start()
            
            # Start offline sync monitor
            sync_thread = threading.Thread(target=self.monitor_offline_sync)
            sync_thread.daemon = True
            sync_thread.start()
    
    def monitor_offline_sync(self):
        """Monitor and sync offline entries periodically"""
        while True:
            try:
                with self.app.app_context():
                    synced_count = db_manager.sync_offline_entries(self.app)
                    if synced_count > 0:
                        print(f"📊 Synced {synced_count} offline entries")
                        realtime_sync.broadcast_system_message(
                            f"Synced {synced_count} offline entries",
                            "info"
                        )
            except Exception as e:
                print(f"⚠️  Sync monitor error: {str(e)}")
            
            time.sleep(30)  # Check every 30 seconds
    
    def open_browser(self, url, delay=2):
        """Open browser after a delay"""
        def delayed_open():
            time.sleep(delay)
            try:
                webbrowser.open(url)
            except Exception as e:
                print(f"Could not open browser: {str(e)}")
        
        threading.Thread(target=delayed_open).start()
    
    def run(self):
        """Run the WikiDesk application"""
        print("🚀 Starting WikiDesk...")
        print("=" * 50)
        
        # Check configuration
        if not self.config:
            print("❌ No configuration found!")
            print("Please run the installation wizard first.")
            input("Press Enter to exit...")
            return
        
        # Create Flask app
        self.app = create_app()
        
        # Initialize database
        if not self.initialize_database():
            input("Press Enter to exit...")
            return
        
        # Get configuration
        server_config = self.config["server"]
        host = server_config["host"]
        port = server_config["port"]
        
        # Print startup information
        print(f"📡 Mode: {'Server' if self.is_server_mode else 'Client'}")
        print(f"🌐 Host: {host}")
        print(f"🔌 Port: {port}")
        print(f"🗄️  Database: {self.config['database']['host']}")
        print(f"👤 Role: {self.config['user']['role']}")
        print("=" * 50)
        
        # Start background tasks
        self.start_background_tasks()
        
        # Open browser for client mode
        if not self.is_server_mode:
            url = f"http://{host}:{port}"
            print(f"🌍 Opening browser: {url}")
            self.open_browser(url)
        
        # Start the application
        try:
            print("✅ WikiDesk is running!")
            print("Press Ctrl+C to stop")
            print("=" * 50)
            
            # Run with SocketIO for real-time features
            socketio.run(
                self.app,
                host='0.0.0.0' if self.is_server_mode else host,
                port=port,
                debug=False,
                allow_unsafe_werkzeug=True
            )
            
        except KeyboardInterrupt:
            print("\n⏹️  WikiDesk stopped by user")
        except Exception as e:
            print(f"❌ Application error: {str(e)}")
            input("Press Enter to exit...")

def main():
    """Main entry point"""
    # Handle command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == '--server':
            # Force server mode
            from config.deployment import DeploymentConfig
            config_manager = DeploymentConfig()
            config = config_manager.load_config()
            if config:
                config['user']['role'] = 'server'
                config_manager.create_config(**config)
        elif sys.argv[1] == '--config':
            # Run configuration wizard
            from installer.setup_wizard import WikiDeskInstaller
            installer = WikiDeskInstaller()
            installer.run()
            return
    
    # Launch the application
    launcher = WikiDeskLauncher()
    launcher.run()

if __name__ == "__main__":
    main()
"""
Deployment configuration for WikiDesk LAN deployment
"""
import os
import json
import socket
from pathlib import Path

class DeploymentConfig:
    def __init__(self):
        self.config_dir = Path.home() / ".wikiDesk"
        self.config_file = self.config_dir / "config.json"
        self.config_dir.mkdir(exist_ok=True)
        
    def create_config(self, server_ip, server_port, db_host, db_port, db_name, db_user, db_password, user_role):
        """Create configuration file for client installation"""
        config = {
            "server": {
                "host": server_ip,
                "port": server_port
            },
            "database": {
                "host": db_host,
                "port": db_port,
                "name": db_name,
                "user": db_user,
                "password": db_password,
                "type": "postgresql"
            },
            "user": {
                "role": user_role,
                "pc_name": socket.gethostname(),
                "install_date": str(Path(__file__).stat().st_mtime)
            },
            "features": {
                "real_time_sync": True,
                "offline_mode": True,
                "auto_backup": user_role == "admin"
            }
        }
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        return config
    
    def load_config(self):
        """Load existing configuration"""
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def get_database_url(self):
        """Get database URL for SQLAlchemy"""
        config = self.load_config()
        if not config:
            return None
        
        db = config["database"]
        return f"postgresql://{db['user']}:{db['password']}@{db['host']}:{db['port']}/{db['name']}"
    
    def get_server_url(self):
        """Get server URL for WebSocket connections"""
        config = self.load_config()
        if not config:
            return None
        
        server = config["server"]
        return f"http://{server['host']}:{server['port']}"
    
    def is_server_mode(self):
        """Check if this PC is the server"""
        config = self.load_config()
        if not config:
            return False
        
        return config["user"]["role"] == "server"
    
    def get_local_ip(self):
        """Get local IP address"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

# Configuration for different deployment modes
class NetworkConfig:
    # Default PostgreSQL settings for LAN deployment
    DEFAULT_DB_PORT = 5432
    DEFAULT_APP_PORT = 5000
    
    # Database connection settings
    DB_CONNECTION_TIMEOUT = 30
    DB_MAX_CONNECTIONS = 20
    
    # Real-time sync settings
    WEBSOCKET_PING_INTERVAL = 25
    WEBSOCKET_PING_TIMEOUT = 5
    
    # Offline mode settings
    OFFLINE_CACHE_SIZE = 1000
    SYNC_RETRY_INTERVAL = 30
    
    # Backup settings
    BACKUP_RETENTION_DAYS = 30
    BACKUP_INTERVAL_HOURS = 24

# Global configuration instance
deployment_config = DeploymentConfig()
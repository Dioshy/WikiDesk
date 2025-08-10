"""
Simple deployment configuration using SQLite for easier deployment
No PostgreSQL required - perfect for small office networks
"""
import os
import json
import socket
from pathlib import Path

class SimpleDeploymentConfig:
    def __init__(self):
        self.config_dir = Path.home() / ".wikiDesk"
        self.config_file = self.config_dir / "config.json"
        self.config_dir.mkdir(exist_ok=True)
        
        # Use a shared network SQLite database
        self.shared_db_dir = self.find_shared_location()
        
    def find_shared_location(self):
        """Find or create a shared network location for the database"""
        possible_locations = [
            Path("C:/WikiDesk_Shared"),  # Local shared folder
            Path("//SERVER/WikiDesk"),   # Network share (if available)
            Path.home() / "WikiDesk_Shared"  # User home fallback
        ]
        
        for location in possible_locations:
            try:
                location.mkdir(parents=True, exist_ok=True)
                # Test write access
                test_file = location / "test_write.txt"
                test_file.write_text("test")
                test_file.unlink()
                return location
            except:
                continue
        
        # Fallback to user directory
        fallback = Path.home() / "WikiDesk_Shared"
        fallback.mkdir(exist_ok=True)
        return fallback
    
    def create_config(self, server_ip, server_port, user_role, install_type="client"):
        """Create configuration file for installation"""
        
        # Database will be a shared SQLite file
        db_path = self.shared_db_dir / "wikiDesk.db"
        
        config = {
            "installation": {
                "type": install_type,  # "server" or "client"
                "version": "1.0.0",
                "install_date": str(Path(__file__).stat().st_mtime)
            },
            "server": {
                "host": server_ip,
                "port": server_port
            },
            "database": {
                "type": "sqlite",
                "path": str(db_path),
                "shared_location": str(self.shared_db_dir)
            },
            "user": {
                "role": user_role,
                "pc_name": socket.gethostname(),
                "pc_ip": self.get_local_ip()
            },
            "features": {
                "real_time_sync": True,
                "offline_mode": True,
                "auto_backup": install_type == "server"
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
        """Get database URL for SQLAlchemy (SQLite)"""
        config = self.load_config()
        if not config:
            return None
        
        db_path = config["database"]["path"]
        return f"sqlite:///{db_path}"
    
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
        
        return config["installation"]["type"] == "server"
    
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

# Global configuration instance
simple_deployment_config = SimpleDeploymentConfig()
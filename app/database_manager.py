"""
Database manager for handling PostgreSQL connections and SQLite offline cache
"""
import sqlite3
import json
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from config.deployment import deployment_config, NetworkConfig
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.config = deployment_config.load_config()
        self.offline_db_path = deployment_config.config_dir / "offline_cache.db"
        self.is_online = False
        self._setup_offline_db()
    
    def _setup_offline_db(self):
        """Setup SQLite database for offline caching"""
        conn = sqlite3.connect(self.offline_db_path)
        cursor = conn.cursor()
        
        # Create offline cache tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS offline_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                courtier_id INTEGER,
                minutes INTEGER,
                type_dacte TEXT,
                acte_de_gestion TEXT,
                dossier TEXT,
                client_name TEXT,
                description TEXT,
                entry_date TEXT,
                entry_time TEXT,
                created_at TEXT,
                synced BOOLEAN DEFAULT FALSE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sync_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT,
                table_name TEXT,
                record_id INTEGER,
                timestamp TEXT,
                status TEXT,
                error_message TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def test_connection(self):
        """Test connection to main PostgreSQL database"""
        try:
            if not self.config:
                logger.error("No configuration found")
                return False
            
            db_url = deployment_config.get_database_url()
            engine = create_engine(db_url, pool_timeout=NetworkConfig.DB_CONNECTION_TIMEOUT)
            
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                self.is_online = True
                logger.info("Database connection successful")
                return True
                
        except SQLAlchemyError as e:
            self.is_online = False
            logger.error(f"Database connection failed: {str(e)}")
            return False
    
    def save_offline_entry(self, entry_data):
        """Save entry to offline cache when main DB is unavailable"""
        conn = sqlite3.connect(self.offline_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO offline_entries (
                user_id, courtier_id, minutes, type_dacte, acte_de_gestion,
                dossier, client_name, description, entry_date, entry_time, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            entry_data.get('user_id'),
            entry_data.get('courtier_id'),
            entry_data.get('minutes'),
            entry_data.get('type_dacte'),
            entry_data.get('acte_de_gestion'),
            entry_data.get('dossier'),
            entry_data.get('client_name'),
            entry_data.get('description'),
            entry_data.get('entry_date'),
            entry_data.get('entry_time'),
            datetime.now().isoformat()
        ))
        
        entry_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"Entry saved offline with ID: {entry_id}")
        return entry_id
    
    def get_unsynced_entries(self):
        """Get all entries that haven't been synced to main DB"""
        conn = sqlite3.connect(self.offline_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM offline_entries WHERE synced = FALSE
        ''')
        
        entries = cursor.fetchall()
        conn.close()
        
        return entries
    
    def mark_entry_synced(self, offline_id):
        """Mark an offline entry as synced"""
        conn = sqlite3.connect(self.offline_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE offline_entries SET synced = TRUE WHERE id = ?
        ''', (offline_id,))
        
        conn.commit()
        conn.close()
    
    def sync_offline_entries(self, app):
        """Sync offline entries to main database"""
        if not self.test_connection():
            logger.warning("Cannot sync: main database unavailable")
            return 0
        
        unsynced_entries = self.get_unsynced_entries()
        synced_count = 0
        
        with app.app_context():
            from app.models.entry import Entry
            from app import db
            
            for entry_data in unsynced_entries:
                try:
                    # Create entry in main database
                    entry = Entry(
                        user_id=entry_data[1],
                        courtier_id=entry_data[2],
                        minutes=entry_data[3],
                        type_dacte=entry_data[4],
                        acte_de_gestion=entry_data[5],
                        dossier=entry_data[6],
                        client_name=entry_data[7],
                        description=entry_data[8],
                        entry_date=datetime.fromisoformat(entry_data[9]).date() if entry_data[9] else None,
                        entry_time=datetime.fromisoformat(entry_data[10]).time() if entry_data[10] else None
                    )
                    
                    db.session.add(entry)
                    db.session.commit()
                    
                    # Mark as synced
                    self.mark_entry_synced(entry_data[0])
                    synced_count += 1
                    
                    logger.info(f"Synced offline entry ID: {entry_data[0]}")
                    
                except Exception as e:
                    logger.error(f"Failed to sync entry ID {entry_data[0]}: {str(e)}")
                    db.session.rollback()
        
        logger.info(f"Synced {synced_count} offline entries")
        return synced_count
    
    def create_backup(self, backup_path):
        """Create database backup (PostgreSQL)"""
        if not self.config:
            return False
        
        try:
            db_config = self.config["database"]
            backup_file = backup_path / f"wikiDesk_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
            
            # Use pg_dump for PostgreSQL backup
            import subprocess
            cmd = [
                "pg_dump",
                "-h", db_config["host"],
                "-p", str(db_config["port"]),
                "-U", db_config["user"],
                "-d", db_config["name"],
                "-f", str(backup_file)
            ]
            
            env = os.environ.copy()
            env["PGPASSWORD"] = db_config["password"]
            
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Backup created: {backup_file}")
                return str(backup_file)
            else:
                logger.error(f"Backup failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Backup error: {str(e)}")
            return False

# Global database manager instance
db_manager = DatabaseManager()
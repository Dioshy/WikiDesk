"""
Automated backup scheduler for WikiDesk server
"""
import schedule
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
import shutil
import logging
from app.database_manager import db_manager
from config.deployment import NetworkConfig

logger = logging.getLogger(__name__)

class BackupScheduler:
    def __init__(self, app):
        self.app = app
        self.backup_dir = Path.home() / "WikiDesk_Backups"
        self.backup_dir.mkdir(exist_ok=True)
        
        # Shared network backup path (if configured)
        self.network_backup_dir = None
        self.setup_network_backup()
    
    def setup_network_backup(self):
        """Setup network backup location"""
        # Try to find a shared network location
        possible_paths = [
            Path("//SERVER/WikiDesk_Backups"),
            Path("Z:/WikiDesk_Backups"),  # Mapped network drive
            Path("C:/Shared/WikiDesk_Backups")  # Local shared folder
        ]
        
        for path in possible_paths:
            try:
                if path.exists() or path.parent.exists():
                    path.mkdir(exist_ok=True)
                    self.network_backup_dir = path
                    logger.info(f"Network backup location: {path}")
                    break
            except Exception as e:
                logger.warning(f"Cannot access {path}: {str(e)}")
    
    def create_backup(self):
        """Create a database backup"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Create database backup
            backup_file = db_manager.create_backup(self.backup_dir)
            
            if backup_file:
                logger.info(f"Database backup created: {backup_file}")
                
                # Copy to network location if available
                if self.network_backup_dir:
                    try:
                        network_backup = self.network_backup_dir / Path(backup_file).name
                        shutil.copy2(backup_file, network_backup)
                        logger.info(f"Backup copied to network: {network_backup}")
                    except Exception as e:
                        logger.error(f"Failed to copy backup to network: {str(e)}")
                
                # Clean old backups
                self.cleanup_old_backups()
                
                return backup_file
            else:
                logger.error("Backup creation failed")
                return None
                
        except Exception as e:
            logger.error(f"Backup error: {str(e)}")
            return None
    
    def cleanup_old_backups(self):
        """Remove backups older than retention period"""
        try:
            cutoff_date = datetime.now() - timedelta(days=NetworkConfig.BACKUP_RETENTION_DAYS)
            
            # Clean local backups
            for backup_file in self.backup_dir.glob("wikiDesk_backup_*.sql"):
                if backup_file.stat().st_mtime < cutoff_date.timestamp():
                    backup_file.unlink()
                    logger.info(f"Removed old backup: {backup_file}")
            
            # Clean network backups
            if self.network_backup_dir:
                for backup_file in self.network_backup_dir.glob("wikiDesk_backup_*.sql"):
                    if backup_file.stat().st_mtime < cutoff_date.timestamp():
                        backup_file.unlink()
                        logger.info(f"Removed old network backup: {backup_file}")
                        
        except Exception as e:
            logger.error(f"Backup cleanup error: {str(e)}")
    
    def schedule_backups(self):
        """Schedule automatic backups"""
        # Daily backup at 2:00 AM
        schedule.every().day.at("02:00").do(self.create_backup)
        
        # Weekly backup on Sunday at 1:00 AM
        schedule.every().sunday.at("01:00").do(self.create_weekly_backup)
        
        logger.info("Backup schedule configured:")
        logger.info("- Daily backup: 2:00 AM")
        logger.info("- Weekly backup: Sunday 1:00 AM")
    
    def create_weekly_backup(self):
        """Create a special weekly backup"""
        try:
            backup_file = self.create_backup()
            if backup_file and self.network_backup_dir:
                # Create a special weekly backup copy
                weekly_backup = self.network_backup_dir / f"weekly_{Path(backup_file).name}"
                shutil.copy2(backup_file, weekly_backup)
                logger.info(f"Weekly backup created: {weekly_backup}")
        except Exception as e:
            logger.error(f"Weekly backup error: {str(e)}")
    
    def run_scheduler(self):
        """Run the backup scheduler"""
        logger.info("Starting backup scheduler...")
        
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Scheduler error: {str(e)}")
                time.sleep(60)

def start_backup_scheduler(app):
    """Start the backup scheduler in a separate thread"""
    scheduler = BackupScheduler(app)
    scheduler.schedule_backups()
    
    # Create initial backup
    logger.info("Creating initial backup...")
    scheduler.create_backup()
    
    # Start scheduler
    scheduler.run_scheduler()

# Manual backup function for immediate use
def create_manual_backup(app):
    """Create a manual backup immediately"""
    scheduler = BackupScheduler(app)
    return scheduler.create_backup()
import os
import shutil
import subprocess
import sqlite3
from datetime import datetime, timedelta
from flask import current_app
from app import db

class BackupManager:
    def __init__(self):
        self.backup_path = current_app.config.get('BACKUP_PATH', './backups')
        os.makedirs(self.backup_path, exist_ok=True)
    
    def create_backup(self, backup_type='manual'):
        """Create a database backup"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'backup_{backup_type}_{timestamp}'
        
        database_url = current_app.config.get('SQLALCHEMY_DATABASE_URI')
        
        if database_url.startswith('sqlite:'):
            return self._backup_sqlite(backup_filename, database_url)
        elif database_url.startswith('postgresql:'):
            return self._backup_postgresql(backup_filename, database_url)
        elif database_url.startswith('mysql:'):
            return self._backup_mysql(backup_filename, database_url)
        else:
            raise ValueError(f"Unsupported database type: {database_url}")
    
    def _backup_sqlite(self, backup_filename, database_url):
        """Backup SQLite database"""
        # Extract database file path from URL
        if database_url.startswith('sqlite:///'):
            db_path = database_url[10:]  # Remove 'sqlite:///'
        else:
            db_path = database_url.replace('sqlite://', '')
            
        # Handle Windows paths and resolve relative paths
        if not os.path.isabs(db_path):
            db_path = os.path.abspath(db_path)
            
        backup_file = os.path.join(self.backup_path, f'{backup_filename}.db')
        compressed_file = f'{backup_file}.gz'
        
        try:
            # Check if source database exists
            if not os.path.exists(db_path):
                raise FileNotFoundError(f"Database file not found: {db_path}")
            
            # Close all database connections before backup
            db.engine.dispose()
            
            # Use simple file copy for SQLite (works better on Windows)
            shutil.copy2(db_path, backup_file)
            
            # Compress the backup
            with open(backup_file, 'rb') as f_in:
                import gzip
                with gzip.open(compressed_file, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Remove uncompressed file
            try:
                os.remove(backup_file)
            except:
                pass  # Ignore if file can't be removed
            
            return compressed_file
            
        except Exception as e:
            # Clean up on error
            if os.path.exists(backup_file):
                try:
                    os.remove(backup_file)
                except:
                    pass
            if os.path.exists(compressed_file):
                try:
                    os.remove(compressed_file)
                except:
                    pass
            raise e
    
    def _backup_postgresql(self, backup_filename, database_url):
        """Backup PostgreSQL database using pg_dump"""
        backup_file = os.path.join(self.backup_path, f'{backup_filename}.sql')
        
        # Parse database URL
        import urllib.parse
        url = urllib.parse.urlparse(database_url)
        
        # Build pg_dump command
        env = os.environ.copy()
        if url.password:
            env['PGPASSWORD'] = url.password
        
        cmd = [
            'pg_dump',
            '-h', url.hostname or 'localhost',
            '-p', str(url.port or 5432),
            '-U', url.username or 'postgres',
            '-d', url.path[1:],  # Remove leading slash
            '-f', backup_file,
            '--verbose',
            '--clean',
            '--no-owner',
            '--no-privileges'
        ]
        
        try:
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"pg_dump failed: {result.stderr}")
            
            # Compress the backup
            compressed_file = f'{backup_file}.gz'
            with open(backup_file, 'rb') as f_in:
                import gzip
                with gzip.open(compressed_file, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Remove uncompressed file
            os.remove(backup_file)
            
            return compressed_file
            
        except Exception as e:
            if os.path.exists(backup_file):
                os.remove(backup_file)
            raise e
    
    def _backup_mysql(self, backup_filename, database_url):
        """Backup MySQL database using mysqldump"""
        backup_file = os.path.join(self.backup_path, f'{backup_filename}.sql')
        
        # Parse database URL
        import urllib.parse
        url = urllib.parse.urlparse(database_url)
        
        # Build mysqldump command
        cmd = [
            'mysqldump',
            f'--host={url.hostname or "localhost"}',
            f'--port={url.port or 3306}',
            f'--user={url.username}',
            '--single-transaction',
            '--routines',
            '--triggers',
            '--result-file=' + backup_file
        ]
        
        if url.password:
            cmd.append(f'--password={url.password}')
        
        cmd.append(url.path[1:])  # Database name, remove leading slash
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"mysqldump failed: {result.stderr}")
            
            # Compress the backup
            compressed_file = f'{backup_file}.gz'
            with open(backup_file, 'rb') as f_in:
                import gzip
                with gzip.open(compressed_file, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Remove uncompressed file
            os.remove(backup_file)
            
            return compressed_file
            
        except Exception as e:
            if os.path.exists(backup_file):
                os.remove(backup_file)
            raise e
    
    def restore_backup(self, backup_file):
        """Restore database from backup"""
        if not os.path.exists(backup_file):
            raise FileNotFoundError(f"Backup file not found: {backup_file}")
        
        database_url = current_app.config.get('SQLALCHEMY_DATABASE_URI')
        
        # Decompress if needed
        if backup_file.endswith('.gz'):
            import gzip
            temp_file = backup_file[:-3]  # Remove .gz extension
            with gzip.open(backup_file, 'rb') as f_in:
                with open(temp_file, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            backup_file = temp_file
        
        try:
            if database_url.startswith('sqlite:'):
                self._restore_sqlite(backup_file, database_url)
            elif database_url.startswith('postgresql:'):
                self._restore_postgresql(backup_file, database_url)
            elif database_url.startswith('mysql:'):
                self._restore_mysql(backup_file, database_url)
            else:
                raise ValueError(f"Unsupported database type: {database_url}")
        finally:
            # Clean up temp file if we decompressed
            if backup_file.endswith('.sql') and os.path.exists(backup_file):
                os.remove(backup_file)
    
    def _restore_sqlite(self, backup_file, database_url):
        """Restore SQLite database"""
        # Extract database file path from URL
        if database_url.startswith('sqlite:///'):
            db_path = database_url[10:]  # Remove 'sqlite:///'
        else:
            db_path = database_url.replace('sqlite://', '')
            
        # Handle Windows paths and resolve relative paths
        if not os.path.isabs(db_path):
            db_path = os.path.abspath(db_path)
        
        # Close all connections
        db.engine.dispose()
        
        # Create parent directory if it doesn't exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Replace database file
        if os.path.exists(db_path):
            shutil.copy2(db_path, f'{db_path}.bak')  # Create backup of current
        
        shutil.copy2(backup_file, db_path)
    
    def _restore_postgresql(self, backup_file, database_url):
        """Restore PostgreSQL database"""
        import urllib.parse
        url = urllib.parse.urlparse(database_url)
        
        # Build psql command
        env = os.environ.copy()
        if url.password:
            env['PGPASSWORD'] = url.password
        
        cmd = [
            'psql',
            '-h', url.hostname or 'localhost',
            '-p', str(url.port or 5432),
            '-U', url.username or 'postgres',
            '-d', url.path[1:],
            '-f', backup_file
        ]
        
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"psql restore failed: {result.stderr}")
    
    def _restore_mysql(self, backup_file, database_url):
        """Restore MySQL database"""
        import urllib.parse
        url = urllib.parse.urlparse(database_url)
        
        # Build mysql command
        cmd = [
            'mysql',
            f'--host={url.hostname or "localhost"}',
            f'--port={url.port or 3306}',
            f'--user={url.username}'
        ]
        
        if url.password:
            cmd.append(f'--password={url.password}')
        
        cmd.append(url.path[1:])  # Database name
        
        with open(backup_file, 'r') as f:
            result = subprocess.run(cmd, stdin=f, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"mysql restore failed: {result.stderr}")
    
    def list_backups(self):
        """List all available backups"""
        backups = []
        
        if not os.path.exists(self.backup_path):
            return backups
        
        for filename in os.listdir(self.backup_path):
            if filename.startswith('backup_'):
                filepath = os.path.join(self.backup_path, filename)
                stat = os.stat(filepath)
                
                # Parse backup info from filename
                parts = filename.replace('.gz', '').replace('.sql', '').replace('.db', '').split('_')
                backup_type = parts[1] if len(parts) > 1 else 'unknown'
                timestamp_str = parts[2] if len(parts) > 2 else ''
                
                try:
                    timestamp = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
                except ValueError:
                    timestamp = datetime.fromtimestamp(stat.st_mtime)
                
                backups.append({
                    'filename': filename,
                    'filepath': filepath,
                    'type': backup_type,
                    'timestamp': timestamp,
                    'size': stat.st_size,
                    'size_mb': round(stat.st_size / (1024 * 1024), 2)
                })
        
        # Sort by timestamp, newest first
        backups.sort(key=lambda x: x['timestamp'], reverse=True)
        return backups
    
    def delete_backup(self, filename):
        """Delete a specific backup file"""
        filepath = os.path.join(self.backup_path, filename)
        
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Backup file not found: {filename}")
        
        os.remove(filepath)
    
    def cleanup_old_backups(self, keep_days=30, keep_count=10):
        """Clean up old backup files"""
        backups = self.list_backups()
        
        # Keep at least keep_count backups
        if len(backups) <= keep_count:
            return []
        
        # Delete backups older than keep_days
        cutoff_date = datetime.now() - timedelta(days=keep_days)
        deleted_files = []
        
        for backup in backups[keep_count:]:  # Skip the newest keep_count backups
            if backup['timestamp'] < cutoff_date:
                try:
                    self.delete_backup(backup['filename'])
                    deleted_files.append(backup['filename'])
                except Exception as e:
                    print(f"Failed to delete backup {backup['filename']}: {e}")
        
        return deleted_files
    
    def schedule_automatic_backup(self):
        """Set up automatic daily backups using APScheduler"""
        from apscheduler.schedulers.background import BackgroundScheduler
        import atexit
        
        scheduler = BackgroundScheduler()
        
        # Daily backup at 2 AM
        scheduler.add_job(
            func=lambda: self.create_backup('auto_daily'),
            trigger="cron",
            hour=2,
            minute=0,
            id='daily_backup',
            replace_existing=True
        )
        
        # Weekly cleanup on Sundays at 3 AM
        scheduler.add_job(
            func=self.cleanup_old_backups,
            trigger="cron",
            day_of_week=6,  # Sunday
            hour=3,
            minute=0,
            id='backup_cleanup',
            replace_existing=True
        )
        
        scheduler.start()
        
        # Shut down the scheduler when exiting the app
        atexit.register(lambda: scheduler.shutdown())
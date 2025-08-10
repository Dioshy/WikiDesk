from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from app import db

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.Enum('admin', 'user', name='user_roles'), default='user', nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationship with entries
    entries = db.relationship('Entry', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def __init__(self, username, email, full_name, password, role='user'):
        self.username = username
        self.email = email
        self.full_name = full_name
        self.set_password(password)
        self.role = role
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        return self.role == 'admin'
    
    def get_stats(self, start_date=None, end_date=None):
        """Get user statistics for a date range"""
        from datetime import date, timedelta
        from sqlalchemy import func
        from app.models.entry import Entry
        
        query = self.entries
        
        if start_date:
            query = query.filter(Entry.date >= start_date)
        if end_date:
            query = query.filter(Entry.date <= end_date)
            
        entries = query.all()
        
        total_minutes = sum(entry.minutes for entry in entries)
        total_calls = len(entries)
        
        # Today's stats
        today = date.today()
        today_entries = self.entries.filter(Entry.date == today).all()
        today_count = len(today_entries)
        
        # This week's stats
        week_ago = today - timedelta(days=7)
        week_entries = self.entries.filter(Entry.date >= week_ago, Entry.date <= today).count()
        
        # This month's stats
        month_start = today.replace(day=1)
        month_entries = self.entries.filter(Entry.date >= month_start, Entry.date <= today).count()
        
        # Max daily entries
        daily_counts = db.session.query(Entry.date, func.count(Entry.id).label('count')).filter(
            Entry.user_id == self.id
        ).group_by(Entry.date).all()
        max_daily = max([row.count for row in daily_counts]) if daily_counts else 0
        
        # Average minutes per entry
        average_minutes = total_minutes / total_calls if total_calls > 0 else 0
        
        # Top clients
        client_stats = {}
        for entry in entries:
            if entry.client_name:
                client_stats[entry.client_name] = client_stats.get(entry.client_name, 0) + entry.minutes
        
        top_clients = sorted(client_stats.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            'total_minutes': total_minutes,
            'total_calls': total_calls,
            'total_entries': total_calls,  # Alias for compatibility
            'today_entries': today_count,
            'week_entries': week_entries,
            'month_entries': month_entries,
            'max_daily': max_daily,
            'average_minutes': average_minutes,
            'top_clients': top_clients
        }
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'role': self.role,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }
    
    def __repr__(self):
        return f'<User {self.username}>'
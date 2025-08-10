from app import db
from datetime import datetime

class Courtier(db.Model):
    __tablename__ = 'courtiers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    odoo_so_id = db.Column(db.String(50), unique=True, nullable=True, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with entries
    entries = db.relationship('Entry', backref='courtier', lazy='dynamic')
    
    def __init__(self, name, odoo_so_id=None):
        self.name = name
        self.odoo_so_id = odoo_so_id
    
    def get_total_minutes(self, start_date=None, end_date=None):
        """Get total minutes for this courtier within a date range"""
        query = self.entries
        
        if start_date:
            query = query.filter(Entry.date >= start_date)
        if end_date:
            query = query.filter(Entry.date <= end_date)
            
        return sum(entry.minutes for entry in query.all())
    
    def get_entries_count(self, start_date=None, end_date=None):
        """Get total number of entries for this courtier within a date range"""
        query = self.entries
        
        if start_date:
            query = query.filter(Entry.date >= start_date)
        if end_date:
            query = query.filter(Entry.date <= end_date)
            
        return query.count()
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'odoo_so_id': self.odoo_so_id,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<Courtier {self.name}>'
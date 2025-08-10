from app import db
from datetime import datetime, date
from sqlalchemy import Index

class Entry(db.Model):
    __tablename__ = 'entries'
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, index=True, default=date.today)
    time = db.Column(db.Time, nullable=False, default=lambda: datetime.now().time())
    period = db.Column(db.String(6), nullable=False, index=True)  # YYYYMM format
    
    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    courtier_id = db.Column(db.Integer, db.ForeignKey('courtiers.id'), nullable=False, index=True)
    
    # Entry data
    minutes = db.Column(db.Integer, nullable=False)  # Duration in minutes
    acte_de_gestion = db.Column(db.String(200), nullable=True)  # Free text field
    acte_type = db.Column(db.Enum('Gestion sinistre', 'Production', 'Bloc retour',
                                 name='acte_type_enum'), nullable=False, default='Gestion sinistre')
    type_dacte = db.Column(db.Enum('Gestion sinistre', 'Production', 'Bloc retour',
                                  name='type_dacte'), nullable=True, default='Gestion sinistre')
    dossier = db.Column(db.String(100), nullable=True)
    client_name = db.Column(db.String(200), nullable=True, index=True)
    description = db.Column(db.Text, nullable=True)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __init__(self, user_id, courtier_id, minutes, type_dacte, 
                 acte_de_gestion=None, dossier=None, client_name=None, description=None, 
                 entry_date=None, entry_time=None):
        self.user_id = user_id
        self.courtier_id = courtier_id
        self.minutes = minutes
        # Set both fields to ensure database compatibility
        self.type_dacte = type_dacte
        self.acte_type = type_dacte  # Use same value for database compatibility
        self.acte_de_gestion = acte_de_gestion
        self.dossier = dossier
        self.client_name = client_name
        self.description = description
        
        # Set date and time
        if entry_date:
            self.date = entry_date
        else:
            self.date = date.today()
            
        if entry_time:
            self.time = entry_time
        else:
            self.time = datetime.now().time()
        
        # Generate period (YYYYMM)
        self.period = self.date.strftime('%Y%m')
    
    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.isoformat(),
            'time': self.time.strftime('%H:%M:%S'),
            'period': self.period,
            'user_id': self.user_id,
            'courtier_id': self.courtier_id,
            'minutes': self.minutes,
            'type_dacte': self.type_dacte,
            'acte_type': self.acte_type,  # Include for backward compatibility
            'acte_de_gestion': self.acte_de_gestion,
            'dossier': self.dossier,
            'client_name': self.client_name,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'courtier_name': self.courtier.name if self.courtier else None,
            'user_name': self.user.full_name if self.user else None
        }
    
    @staticmethod
    def get_period_from_date(entry_date):
        """Generate period string (YYYYMM) from date"""
        return entry_date.strftime('%Y%m')
    
    @classmethod
    def get_entries_by_period(cls, period, user_id=None):
        """Get all entries for a specific period, optionally filtered by user"""
        query = cls.query.filter(cls.period == period)
        if user_id:
            query = query.filter(cls.user_id == user_id)
        return query.all()
    
    @classmethod
    def get_daily_totals(cls, user_id=None, start_date=None, end_date=None):
        """Get daily totals for charting"""
        query = cls.query
        
        if user_id:
            query = query.filter(cls.user_id == user_id)
        if start_date:
            query = query.filter(cls.date >= start_date)
        if end_date:
            query = query.filter(cls.date <= end_date)
            
        entries = query.all()
        
        # Group by date
        daily_totals = {}
        for entry in entries:
            date_str = entry.date.isoformat()
            daily_totals[date_str] = daily_totals.get(date_str, 0) + entry.minutes
            
        return daily_totals
    
    def __repr__(self):
        return f'<Entry {self.id}: {self.minutes}min on {self.date}>'

# Create composite indexes for better query performance
Index('idx_entry_user_date', Entry.user_id, Entry.date)
Index('idx_entry_courtier_date', Entry.courtier_id, Entry.date)
Index('idx_entry_period_user', Entry.period, Entry.user_id)
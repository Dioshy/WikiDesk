from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.entry import Entry
from app.models.courtier import Courtier
from datetime import date, datetime

api_bp = Blueprint('api', __name__)

@api_bp.route('/entries', methods=['GET'])
@login_required
def get_entries():
    """Get entries with optional filters"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # Base query
    query = Entry.query
    
    # Apply user filter (non-admins can only see their own entries)
    if not current_user.is_admin():
        query = query.filter(Entry.user_id == current_user.id)
    else:
        user_id = request.args.get('user_id', type=int)
        if user_id:
            query = query.filter(Entry.user_id == user_id)
    
    # Apply date filters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if start_date:
        query = query.filter(Entry.date >= datetime.strptime(start_date, '%Y-%m-%d').date())
    if end_date:
        query = query.filter(Entry.date <= datetime.strptime(end_date, '%Y-%m-%d').date())
    
    # Apply other filters
    courtier_id = request.args.get('courtier_id', type=int)
    if courtier_id:
        query = query.filter(Entry.courtier_id == courtier_id)
    
    acte_type = request.args.get('acte_type')
    if acte_type:
        query = query.filter(Entry.acte_type == acte_type)
    
    client_name = request.args.get('client_name')
    if client_name:
        query = query.filter(Entry.client_name.ilike(f'%{client_name}%'))
    
    # Order by date descending
    query = query.order_by(Entry.created_at.desc())
    
    # Paginate
    entries = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'entries': [entry.to_dict() for entry in entries.items],
        'total': entries.total,
        'pages': entries.pages,
        'current_page': page,
        'per_page': per_page
    })

@api_bp.route('/entries', methods=['POST'])
@login_required
def create_entry():
    """Create a new entry via API"""
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['courtier_id', 'minutes', 'type_dacte']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    try:
        entry = Entry(
            user_id=current_user.id,
            courtier_id=data['courtier_id'],
            minutes=data['minutes'],
            type_dacte=data['type_dacte'],
            acte_de_gestion=data.get('acte_de_gestion'),
            dossier=data.get('dossier'),
            client_name=data.get('client_name'),
            description=data.get('description')
        )
        
        # Handle custom date/time if provided
        if 'date' in data:
            entry.date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        if 'time' in data:
            entry.time = datetime.strptime(data['time'], '%H:%M').time()
        
        db.session.add(entry)
        db.session.commit()
        
        return jsonify({
            'message': 'Entry created successfully',
            'entry': entry.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@api_bp.route('/entries/<int:entry_id>', methods=['PUT'])
@login_required
def update_entry(entry_id):
    """Update an existing entry"""
    entry = Entry.query.get_or_404(entry_id)
    
    # Check permissions
    if not current_user.is_admin() and entry.user_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    
    try:
        # Update allowed fields
        allowed_fields = ['courtier_id', 'minutes', 'type_dacte', 'acte_de_gestion', 'dossier', 'client_name', 'description']
        for field in allowed_fields:
            if field in data:
                setattr(entry, field, data[field])
        
        # Handle date/time updates
        if 'date' in data:
            entry.date = datetime.strptime(data['date'], '%Y-%m-%d').date()
            entry.period = entry.date.strftime('%Y%m')
        
        if 'time' in data:
            entry.time = datetime.strptime(data['time'], '%H:%M').time()
        
        entry.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Entry updated successfully',
            'entry': entry.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@api_bp.route('/entries/<int:entry_id>', methods=['DELETE'])
@login_required
def delete_entry(entry_id):
    """Delete an entry"""
    entry = Entry.query.get_or_404(entry_id)
    
    # Check permissions
    if not current_user.is_admin() and entry.user_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        db.session.delete(entry)
        db.session.commit()
        
        return jsonify({'message': 'Entry deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@api_bp.route('/courtiers', methods=['GET'])
@login_required
def get_courtiers():
    """Get list of courtiers"""
    courtiers = Courtier.query.filter_by(is_active=True).all()
    return jsonify({
        'courtiers': [courtier.to_dict() for courtier in courtiers]
    })

@api_bp.route('/stats/dashboard', methods=['GET'])
@login_required
def get_dashboard_stats():
    """Get dashboard statistics for current user"""
    user_id = current_user.id if not current_user.is_admin() else request.args.get('user_id', current_user.id, type=int)
    
    # Today's stats
    today = date.today()
    today_entries = Entry.query.filter(
        Entry.user_id == user_id,
        Entry.date == today
    ).all()
    
    today_minutes = sum(entry.minutes for entry in today_entries)
    today_calls = len(today_entries)
    
    # Weekly chart data
    from datetime import timedelta
    week_ago = today - timedelta(days=6)
    daily_totals = Entry.get_daily_totals(
        user_id=user_id,
        start_date=week_ago,
        end_date=today
    )
    
    # Fill missing dates with 0
    chart_data = {}
    for i in range(7):
        chart_date = (week_ago + timedelta(days=i)).isoformat()
        chart_data[chart_date] = daily_totals.get(chart_date, 0)
    
    return jsonify({
        'today_minutes': today_minutes,
        'today_calls': today_calls,
        'chart_data': chart_data
    })

@api_bp.route('/sync', methods=['POST'])
@login_required
def sync_offline_entries():
    """Sync offline entries when connection is restored"""
    data = request.get_json()
    entries_data = data.get('entries', [])
    
    synced_entries = []
    errors = []
    
    for entry_data in entries_data:
        try:
            entry = Entry(
                user_id=current_user.id,
                courtier_id=entry_data['courtier_id'],
                minutes=entry_data['minutes'],
                type_dacte=entry_data.get('type_dacte', 'Appel téléphonique'),
                acte_de_gestion=entry_data.get('acte_de_gestion'),
                dossier=entry_data.get('dossier'),
                client_name=entry_data.get('client_name'),
                description=entry_data.get('description')
            )
            
            # Handle custom date/time
            if 'date' in entry_data:
                entry.date = datetime.strptime(entry_data['date'], '%Y-%m-%d').date()
            if 'time' in entry_data:
                entry.time = datetime.strptime(entry_data['time'], '%H:%M').time()
            
            db.session.add(entry)
            db.session.commit()
            synced_entries.append(entry.to_dict())
            
        except Exception as e:
            db.session.rollback()
            errors.append({
                'entry': entry_data,
                'error': str(e)
            })
    
    return jsonify({
        'synced': len(synced_entries),
        'errors': len(errors),
        'synced_entries': synced_entries,
        'error_details': errors
    })
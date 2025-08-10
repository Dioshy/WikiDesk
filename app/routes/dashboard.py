from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.models.user import User
from app.models.entry import Entry
from app.models.courtier import Courtier
from app.forms import EntryForm, CourtierForm
from datetime import date, datetime, timedelta

# Try to import SocketIO
try:
    from flask_socketio import emit
    from app import socketio
    SOCKETIO_AVAILABLE = True
except ImportError:
    SOCKETIO_AVAILABLE = False
    socketio = None

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def index():
    # Get user stats for today
    today = date.today()
    today_entries = Entry.query.filter(
        Entry.user_id == current_user.id,
        Entry.date == today
    ).all()
    
    # Calculate stats
    today_minutes = sum(entry.minutes for entry in today_entries)
    today_calls = len(today_entries)
    
    # Get last 7 days for chart - current user
    week_ago = today - timedelta(days=7)
    daily_totals = Entry.get_daily_totals(
        user_id=current_user.id,
        start_date=week_ago,
        end_date=today
    )
    
    # Get all users' activity for multi-user chart
    all_users = User.query.filter_by(is_active=True).all()
    multi_user_data = {}
    
    for user in all_users:
        user_daily_totals = Entry.get_daily_totals(
            user_id=user.id,
            start_date=week_ago,
            end_date=today
        )
        multi_user_data[user.id] = {
            'name': user.full_name,
            'data': user_daily_totals,
            'is_current': user.id == current_user.id
        }
    
    # Get user's overall stats
    user_stats = current_user.get_stats()
    
    # Get courtiers for the form
    courtiers = Courtier.query.filter_by(is_active=True).all()
    
    form = EntryForm()
    form.courtier_id.choices = [(c.id, c.name) for c in courtiers]
    
    return render_template('dashboard/index.html', 
                         form=form,
                         courtiers=courtiers,
                         today_minutes=today_minutes,
                         today_calls=today_calls,
                         daily_totals=daily_totals,
                         multi_user_data=multi_user_data,
                         user_stats=user_stats)

@dashboard_bp.route('/add-entry', methods=['POST'])
@login_required
def add_entry():
    form = EntryForm()
    courtiers = Courtier.query.filter_by(is_active=True).all()
    form.courtier_id.choices = [(c.id, c.name) for c in courtiers]
    
    if form.validate_on_submit():
        entry = Entry(
            user_id=current_user.id,
            courtier_id=form.courtier_id.data,
            minutes=form.minutes.data,
            type_dacte=form.type_dacte.data,
            acte_de_gestion=form.acte_de_gestion.data,
            dossier=form.dossier.data,
            client_name=form.client_name.data,
            description=form.description.data,
            entry_date=form.date.data,
            entry_time=form.time.data
        )
        
        db.session.add(entry)
        db.session.commit()
        
        # Emit real-time update if SocketIO is available
        if SOCKETIO_AVAILABLE and socketio:
            socketio.emit('entry_added', {
                'entry': entry.to_dict(),
                'user_id': current_user.id
            })
        
        flash('Entrée ajoutée avec succès!', 'success')
        return redirect(url_for('dashboard.index'))
    
    # If form has errors, re-render dashboard with errors
    flash('Veuillez vérifier le formulaire pour les erreurs', 'error')
    return redirect(url_for('dashboard.index'))

@dashboard_bp.route('/api/stats')
@login_required
def api_stats():
    """API endpoint for real-time stats"""
    today = date.today()
    today_entries = Entry.query.filter(
        Entry.user_id == current_user.id,
        Entry.date == today
    ).all()
    
    today_minutes = sum(entry.minutes for entry in today_entries)
    today_calls = len(today_entries)
    
    return jsonify({
        'today_minutes': today_minutes,
        'today_calls': today_calls,
        'last_entry': today_entries[-1].to_dict() if today_entries else None
    })

@dashboard_bp.route('/api/chart-data')
@login_required
def api_chart_data():
    """API endpoint for chart data"""
    days = request.args.get('days', 7, type=int)
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    
    daily_totals = Entry.get_daily_totals(
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date
    )
    
    return jsonify(daily_totals)

@dashboard_bp.route('/courtiers')
@login_required
def courtiers():
    """View and manage courtiers for regular users"""
    courtiers = Courtier.query.all()
    form = CourtierForm()
    return render_template('dashboard/courtiers.html', courtiers=courtiers, form=form)

@dashboard_bp.route('/courtiers/add', methods=['POST'])
@login_required
def add_courtier():
    """Add a new courtier (available for all users)"""
    # Check if it's an AJAX request
    if request.headers.get('Content-Type') == 'application/x-www-form-urlencoded' and not request.args.get('redirect'):
        # AJAX request from the dropdown
        name = request.form.get('name', '').strip()
        if not name:
            return jsonify({'success': False, 'error': 'Le nom du courtier est requis'}), 400
        
        # Check if courtier with same name already exists
        existing = Courtier.query.filter_by(name=name).first()
        if existing:
            return jsonify({'success': False, 'error': f'Le courtier {name} existe déjà'}), 400
        
        # Create new courtier
        courtier = Courtier(name=name)
        db.session.add(courtier)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'courtier': {
                'id': courtier.id,
                'name': courtier.name
            }
        })
    
    # Regular form submission
    form = CourtierForm()
    if form.validate_on_submit():
        # Check if courtier with same name already exists
        existing = Courtier.query.filter_by(name=form.name.data).first()
        if existing:
            flash(f'Le courtier {form.name.data} existe déjà!', 'error')
        else:
            courtier = Courtier(
                name=form.name.data,
                odoo_so_id=form.odoo_so_id.data
            )
            db.session.add(courtier)
            db.session.commit()
            flash(f'Courtier {courtier.name} ajouté avec succès!', 'success')
    else:
        flash('Veuillez vérifier le formulaire pour les erreurs', 'error')
    
    return redirect(url_for('dashboard.courtiers'))

@dashboard_bp.route('/courtiers/delete/<int:courtier_id>', methods=['POST'])
@login_required
def delete_courtier(courtier_id):
    """Delete a courtier"""
    courtier = Courtier.query.get_or_404(courtier_id)
    
    # Check if courtier has any entries
    entry_count = Entry.query.filter_by(courtier_id=courtier_id).count()
    
    if entry_count > 0:
        flash(f'Impossible de supprimer {courtier.name}. Ce courtier a {entry_count} entrées associées.', 'error')
    else:
        courtier_name = courtier.name
        db.session.delete(courtier)
        db.session.commit()
        flash(f'Courtier {courtier_name} supprimé avec succès!', 'success')
    
    return redirect(url_for('dashboard.courtiers'))

# WebSocket events (only if SocketIO is available)
if SOCKETIO_AVAILABLE and socketio:
    @socketio.on('connect')
    def handle_connect():
        if current_user.is_authenticated:
            emit('connected', {'user': current_user.full_name})
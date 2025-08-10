from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, send_file
from flask_login import login_required, current_user
from functools import wraps
from app import db
from app.models.user import User
from app.models.entry import Entry
from app.models.courtier import Courtier
from app.forms import CourtierForm
from datetime import date, datetime, timedelta
from sqlalchemy import func, desc
import os
import subprocess
import platform

# Try to import optional utilities
try:
    from app.utils.export import ExcelExporter
    EXPORT_AVAILABLE = True
except ImportError:
    EXPORT_AVAILABLE = False
    
try:
    from app.utils.backup import BackupManager
    BACKUP_AVAILABLE = True
except ImportError:
    BACKUP_AVAILABLE = False

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin():
            flash('Accès refusé. Privilèges administrateur requis.', 'error')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/')
@login_required
@admin_required
def index():
    # Get overview stats
    total_users = User.query.filter_by(is_active=True).count()
    total_entries = Entry.query.count()
    today_entries = Entry.query.filter(Entry.date == date.today()).count()
    
    # Get recent entries
    recent_entries = Entry.query.order_by(desc(Entry.created_at)).limit(10).all()
    
    # Get top users this month
    current_month = date.today().strftime('%Y%m')
    top_users = db.session.query(
        User.full_name,
        func.sum(Entry.minutes).label('total_minutes'),
        func.count(Entry.id).label('total_entries')
    ).join(Entry).filter(
        Entry.period == current_month
    ).group_by(User.id).order_by(desc('total_minutes')).limit(5).all()
    
    # Get top clients this month
    top_clients = db.session.query(
        Entry.client_name,
        func.sum(Entry.minutes).label('total_minutes'),
        func.count(Entry.id).label('total_entries')
    ).filter(
        Entry.period == current_month,
        Entry.client_name.isnot(None)
    ).group_by(Entry.client_name).order_by(desc('total_minutes')).limit(5).all()
    
    return render_template('admin/index.html',
                         total_users=total_users,
                         total_entries=total_entries,
                         today_entries=today_entries,
                         recent_entries=recent_entries,
                         top_users=top_users,
                         top_clients=top_clients)

@admin_bp.route('/users')
@login_required
@admin_required
def users():
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/users/<int:user_id>/toggle-status')
@login_required
@admin_required
def toggle_user_status(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active
    db.session.commit()
    
    status = 'activé' if user.is_active else 'désactivé'
    flash(f'L\'utilisateur {user.full_name} a été {status}', 'success')
    return redirect(url_for('admin.users'))

@admin_bp.route('/courtiers')
@login_required
@admin_required
def courtiers():
    # Redirect admin to the user courtiers page
    return redirect(url_for('dashboard.courtiers'))

@admin_bp.route('/courtiers/add', methods=['POST'])
@login_required
@admin_required
def add_courtier():
    # Redirect to dashboard add_courtier
    return redirect(url_for('dashboard.add_courtier'), code=307)

@admin_bp.route('/courtiers/<int:courtier_id>/toggle-status')
@login_required
@admin_required
def toggle_courtier_status(courtier_id):
    courtier = Courtier.query.get_or_404(courtier_id)
    courtier.is_active = not courtier.is_active
    db.session.commit()
    
    status = 'activé' if courtier.is_active else 'désactivé'
    flash(f'Courtier {courtier.name} a été {status}', 'success')
    return redirect(url_for('dashboard.courtiers'))

@admin_bp.route('/reports')
@login_required
@admin_required
def reports():
    # Calculate current month stats
    current_month = date.today().strftime('%Y%m')
    current_month_entries = Entry.query.filter(Entry.period == current_month).count()
    current_month_minutes = db.session.query(func.sum(Entry.minutes)).filter(Entry.period == current_month).scalar() or 0
    
    # Calculate current year stats
    current_year = date.today().year
    start_of_year = date(current_year, 1, 1)
    end_of_year = date(current_year, 12, 31)
    current_year_entries = Entry.query.filter(
        Entry.date >= start_of_year,
        Entry.date <= end_of_year
    ).count()
    current_year_minutes = db.session.query(func.sum(Entry.minutes)).filter(
        Entry.date >= start_of_year,
        Entry.date <= end_of_year
    ).scalar() or 0
    
    return render_template('admin/reports.html',
                         current_month_entries=current_month_entries,
                         current_month_minutes=current_month_minutes,
                         current_year_entries=current_year_entries,
                         current_year_minutes=current_year_minutes)

@admin_bp.route('/export/<period>')
@login_required
@admin_required
def export_report(period):
    """Export report for a given period (daily, monthly, yearly)"""
    if not EXPORT_AVAILABLE:
        flash('Export functionality not available. Please install pandas and openpyxl.', 'error')
        return redirect(url_for('admin.reports'))
    
    try:
        exporter = ExcelExporter()
        
        if period == 'daily':
            filename = exporter.export_daily_report(date.today())
        elif period == 'monthly':
            current_month = date.today().strftime('%Y%m')
            filename = exporter.export_monthly_report(current_month)
        elif period == 'yearly':
            current_year = date.today().year
            filename = exporter.export_yearly_report(current_year)
        else:
            flash('Invalid export period', 'error')
            return redirect(url_for('admin.reports'))
        
        # Get absolute path
        abs_path = os.path.abspath(filename)
        
        # Open file location dialog on Windows
        if platform.system() == 'Windows':
            try:
                # Open Windows Explorer and select the file
                subprocess.Popen(f'explorer /select,"{abs_path}"')
                flash(f'Report exported successfully! File saved to: {filename}', 'success')
            except Exception as e:
                # Fallback: just open the exports folder
                exports_dir = os.path.dirname(abs_path)
                os.startfile(exports_dir)
                flash(f'Report exported successfully! Check exports folder.', 'success')
        else:
            # For non-Windows systems, return the file as download
            return send_file(filename, as_attachment=True)
        
        return redirect(url_for('admin.reports'))
        
    except Exception as e:
        flash(f'Error generating report: {str(e)}', 'error')
        return redirect(url_for('admin.reports'))

@admin_bp.route('/backup')
@login_required
@admin_required
def backup():
    if not BACKUP_AVAILABLE:
        return render_template('admin/backup.html', backups=[], backup_available=False)
    
    backup_manager = BackupManager()
    backups = backup_manager.list_backups()
    return render_template('admin/backup.html', backups=backups, backup_available=True)

@admin_bp.route('/backup/create')
@login_required
@admin_required
def create_backup():
    """Create manual backup"""
    if not BACKUP_AVAILABLE:
        flash('Backup functionality not available. Please install required dependencies.', 'error')
        return redirect(url_for('admin.backup'))
    
    try:
        backup_manager = BackupManager()
        backup_file = backup_manager.create_backup()
        flash(f'Backup created successfully: {backup_file}', 'success')
    except Exception as e:
        flash(f'Error creating backup: {str(e)}', 'error')
    
    return redirect(url_for('admin.backup'))

@admin_bp.route('/export/open/<period>')
@login_required
@admin_required
def open_export(period):
    """Generate export and open it directly in Excel"""
    if not EXPORT_AVAILABLE:
        flash('Export functionality not available. Please install pandas and openpyxl.', 'error')
        return redirect(url_for('admin.reports'))
    
    try:
        exporter = ExcelExporter()
        
        if period == 'daily':
            filename = exporter.export_daily_report(date.today())
        elif period == 'monthly':
            current_month = date.today().strftime('%Y%m')
            filename = exporter.export_monthly_report(current_month)
        elif period == 'yearly':
            current_year = date.today().year
            filename = exporter.export_yearly_report(current_year)
        else:
            flash('Invalid export period', 'error')
            return redirect(url_for('admin.reports'))
        
        # Get absolute path
        abs_path = os.path.abspath(filename)
        
        # Open file directly in Excel on Windows
        if platform.system() == 'Windows':
            try:
                # Try to open the file directly
                os.startfile(abs_path)
                flash(f'Report opened in Excel! File: {filename}', 'success')
            except Exception as e:
                # Fallback to opening folder
                subprocess.Popen(f'explorer /select,"{abs_path}"')
                flash(f'Report exported! File location opened: {filename}', 'success')
        else:
            # For non-Windows systems, return the file as download
            return send_file(filename, as_attachment=True)
        
        return redirect(url_for('admin.reports'))
        
    except Exception as e:
        flash(f'Error generating report: {str(e)}', 'error')
        return redirect(url_for('admin.reports'))

@admin_bp.route('/api/live-stats')
@login_required
@admin_required
def api_live_stats():
    """API endpoint for live admin statistics"""
    active_users = User.query.filter_by(is_active=True).count()
    today_entries = Entry.query.filter(Entry.date == date.today()).count()
    
    # Get entries from last hour
    last_hour = datetime.utcnow() - timedelta(hours=1)
    recent_activity = Entry.query.filter(Entry.created_at >= last_hour).count()
    
    return jsonify({
        'active_users': active_users,
        'today_entries': today_entries,
        'recent_activity': recent_activity,
        'timestamp': datetime.utcnow().isoformat()
    })
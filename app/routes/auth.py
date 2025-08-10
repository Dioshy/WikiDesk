from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models.user import User
from app.forms import LoginForm, UserRegistrationForm, EditProfileForm, ChangePasswordForm
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        if user and user.check_password(form.password.data) and user.is_active:
            login_user(user, remember=True)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            next_page = request.args.get('next')
            flash(f'Welcome back, {user.full_name}!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('dashboard.index'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('auth/login.html', form=form)

@auth_bp.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    # Only admins can register new users
    if not current_user.is_admin():
        flash('Access denied. Only administrators can register new users.', 'error')
        return redirect(url_for('dashboard.index'))
    
    form = UserRegistrationForm()
    if form.validate_on_submit():
        # Check if username or email already exists
        existing_user = User.query.filter(
            (User.username == form.username.data) | 
            (User.email == form.email.data)
        ).first()
        
        if existing_user:
            flash('Username or email already exists', 'error')
        else:
            user = User(
                username=form.username.data,
                email=form.email.data,
                full_name=form.full_name.data,
                password=form.password.data,
                role=form.role.data
            )
            db.session.add(user)
            db.session.commit()
            flash(f'User {user.full_name} created successfully!', 'success')
            return redirect(url_for('admin.users'))
    
    return render_template('auth/register.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    flash('Vous avez été déconnecté', 'info')
    response = redirect(url_for('auth.login'))
    # Clear any cookies that might be set
    response.set_cookie('remember_token', '', expires=0)
    response.set_cookie('session', '', expires=0)
    return response

@auth_bp.route('/profile')
@login_required
def profile():
    return render_template('auth/profile.html', user=current_user)

@auth_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    
    if form.validate_on_submit():
        # Check if email is being changed and if it's already taken by another user
        if form.email.data != current_user.email:
            existing_user = User.query.filter(
                User.email == form.email.data,
                User.id != current_user.id
            ).first()
            if existing_user:
                flash('Cette adresse email est déjà utilisée par un autre utilisateur.', 'error')
                return render_template('auth/edit_profile.html', form=form)
        
        # Update user information
        current_user.full_name = form.full_name.data
        current_user.email = form.email.data
        
        try:
            db.session.commit()
            flash('Profil mis à jour avec succès!', 'success')
            return redirect(url_for('auth.profile'))
        except Exception as e:
            db.session.rollback()
            flash('Erreur lors de la mise à jour du profil.', 'error')
    
    # Pre-populate form with current user data
    if request.method == 'GET':
        form.full_name.data = current_user.full_name
        form.email.data = current_user.email
    
    return render_template('auth/edit_profile.html', form=form)

@auth_bp.route('/profile/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    
    if form.validate_on_submit():
        # Verify current password
        if not current_user.check_password(form.current_password.data):
            flash('Mot de passe actuel incorrect.', 'error')
            return render_template('auth/change_password.html', form=form)
        
        # Update password
        current_user.set_password(form.new_password.data)
        
        try:
            db.session.commit()
            flash('Mot de passe changé avec succès!', 'success')
            return redirect(url_for('auth.profile'))
        except Exception as e:
            db.session.rollback()
            flash('Erreur lors du changement de mot de passe.', 'error')
    
    return render_template('auth/change_password.html', form=form)
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, IntegerField, TextAreaField, DateField, TimeField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional, EqualTo
from datetime import date, datetime

# Try to import Email validator, fallback to basic validation if not available
try:
    from wtforms.validators import Email
    EMAIL_VALIDATOR_AVAILABLE = True
except ImportError:
    EMAIL_VALIDATOR_AVAILABLE = False
    # Create a basic email validator fallback
    import re
    
    class Email:
        def __init__(self, message=None):
            self.message = message or "Invalid email address."
        
        def __call__(self, form, field):
            if field.data:
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if not re.match(email_pattern, field.data):
                    raise ValueError(self.message)

class LoginForm(FlaskForm):
    username = StringField('Nom d\'utilisateur', validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField('Mot de passe', validators=[DataRequired()])

class UserRegistrationForm(FlaskForm):
    username = StringField('Nom d\'utilisateur', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    full_name = StringField('Nom complet', validators=[DataRequired(), Length(min=2, max=100)])
    password = PasswordField('Mot de passe', validators=[DataRequired(), Length(min=6)])
    role = SelectField('Rôle', choices=[('user', 'Utilisateur standard'), ('admin', 'Administrateur')], default='user')

class EntryForm(FlaskForm):
    date = DateField('Date', default=date.today, validators=[DataRequired()])
    time = TimeField('Heure', default=lambda: datetime.now().time(), validators=[DataRequired()])
    courtier_id = SelectField('Courtier', coerce=int, validators=[DataRequired()])
    minutes = SelectField('Nombre de minutes', 
                         choices=[(i, f'{i} minutes') for i in range(5, 241, 5)],
                         coerce=int, validators=[DataRequired()])
    type_dacte = SelectField('Type d\'acte', 
                           choices=[
                               ('Gestion sinistre', 'Gestion sinistre'),
                               ('Production', 'Production'),
                               ('Bloc retour', 'Bloc retour')
                           ], validators=[DataRequired()])
    acte_de_gestion = StringField('Acte de gestion', validators=[Optional(), Length(max=200)])
    dossier = StringField('Dossier', validators=[Optional(), Length(max=100)])
    client_name = StringField('Nom du client', validators=[Optional(), Length(max=200)])
    description = TextAreaField('Description', validators=[Optional()])

class CourtierForm(FlaskForm):
    name = StringField('Nom du courtier', validators=[DataRequired(), Length(min=2, max=100)])
    odoo_so_id = StringField('ID Odoo SO', validators=[Optional(), Length(max=50)])

class EditProfileForm(FlaskForm):
    full_name = StringField('Nom complet', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Mettre à jour le profil')

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Mot de passe actuel', validators=[DataRequired()])
    new_password = PasswordField('Nouveau mot de passe', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirmer le nouveau mot de passe', 
                                   validators=[DataRequired(), EqualTo('new_password', message='Les mots de passe doivent correspondre')])
    submit = SubmitField('Changer le mot de passe')
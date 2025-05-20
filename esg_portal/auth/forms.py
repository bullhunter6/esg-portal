"""
Authentication forms for user management
"""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectMultipleField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError

from esg_portal.models.user import User

class LoginForm(FlaskForm):
    """Login form"""
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    """Registration form"""
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    first_name = StringField('First Name', validators=[Length(max=64)])
    last_name = StringField('Last Name', validators=[Length(max=64)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(), EqualTo('password')]
    )
    submit = SubmitField('Register')
    
    def validate_username(self, username):
        """Validate that username is unique"""
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')
    
    def validate_email(self, email):
        """Validate that email is unique"""
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')

class ProfileForm(FlaskForm):
    """User profile form"""
    first_name = StringField('First Name', validators=[Length(max=64)])
    last_name = StringField('Last Name', validators=[Length(max=64)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('New Password', validators=[Length(min=8)])
    password2 = PasswordField(
        'Repeat New Password', validators=[EqualTo('password')]
    )
    
    # User preferences
    ESG_CATEGORIES = [
        ('environmental', 'Environmental'),
        ('social', 'Social'),
        ('governance', 'Governance'),
        ('climate', 'Climate Change'),
        ('sustainability', 'Sustainability'),
        ('renewable', 'Renewable Energy'),
        ('diversity', 'Diversity & Inclusion'),
        ('corporate', 'Corporate Governance')
    ]
    
    preferred_categories = SelectMultipleField(
        'Preferred Categories',
        choices=ESG_CATEGORIES
    )
    email_notifications = BooleanField('Receive Email Notifications')
    
    submit = SubmitField('Update Profile')
    
    def validate_email(self, email):
        """Validate that email is unique (except for current user)"""
        from flask_login import current_user
        
        user = User.query.filter_by(email=email.data).first()
        if user is not None and user.id != current_user.id:
            raise ValidationError('Please use a different email address.') 
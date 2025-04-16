from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
import re
from models import User

def is_strong_password(form, field):
    password = field.data
    if (len(password) < 8 or
        not re.search(r'[A-Z]', password) or
        not re.search(r'[a-z]', password) or
        not re.search(r'[0-9]', password) or
        not re.search(r'[!@#$%^&*(),.?":{}|<>]', password)):
        raise ValidationError(
            "Password must be at least 8 characters long, include one uppercase letter, "
            "one lowercase letter, one digit, and one special symbol."
        )

class RoleSelectForm(FlaskForm):
    role = SelectField(
        'I want to sign up as:',
        choices=[('job_seeker', 'Job Seeker'), ('job_recruiter', 'Job Recruiter')],
        validators=[DataRequired()]
    )
    submit = SubmitField('Next')

class JobSeekerSignUpForm(FlaskForm):
    username = StringField(
        'Username',
        validators=[DataRequired(), Length(min=2, max=20, message="Username must be between 2 and 20 characters.")]
    )
    email = StringField(
        'Email',
        validators=[DataRequired(), Email(message="Please enter a valid email address.")]
    )
    password = PasswordField(
        'Password',
        validators=[DataRequired(), is_strong_password]
    )
    confirm_password = PasswordField(
        'Confirm Password',
        validators=[DataRequired(), EqualTo('password', message="Passwords must match.")]
    )
    submit = SubmitField('Sign Up')

    def validate_email(self, email):
        existing_user = User.query.filter_by(email=email.data).first()
        if existing_user:
            raise ValidationError("Email is already registered. Please use a different one or login.")

class RecruiterSignUpForm(FlaskForm):
    organization_name = StringField(
        'Organization Name',
        validators=[DataRequired(), Length(min=2, max=50, message="Organization name must be between 2 and 50 characters.")]
    )
    email = StringField(
        'Email',
        validators=[DataRequired(), Email(message="Please enter a valid email address.")]
    )
    password = PasswordField(
        'Password',
        validators=[DataRequired(), is_strong_password]
    )
    confirm_password = PasswordField(
        'Confirm Password',
        validators=[DataRequired(), EqualTo('password', message="Passwords must match.")]
    )
    submit = SubmitField('Sign Up')

    def validate_email(self, email):
        existing_user = User.query.filter_by(email=email.data).first()
        if existing_user:
            raise ValidationError("Email is already registered. Please use a different one or login.")

class LoginForm(FlaskForm):
    email = StringField(
        'Email',
        validators=[DataRequired(), Email(message="Please enter a valid email address.")]
    )
    password = PasswordField(
        'Password',
        validators=[DataRequired(), Length(min=8, message="Password must be at least 8 characters long.")]
    )
    submit = SubmitField('Login')
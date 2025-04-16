from flask import Flask, render_template, flash, url_for, redirect, session, request
from models import db, User
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
from forms import LoginForm
from signup import signup 
from dashboard import dashboard
from predictor import predictor
import smtplib 
from datetime import datetime
import pytz
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from itsdangerous import URLSafeTimedSerializer
from dotenv import load_dotenv
import os
import re

load_dotenv()
EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS')
LOGIN_PASSWORD = os.getenv('LOGIN_PASSWORD')

app = Flask(__name__)
app.config['SECRET_KEY'] = 'FDKJF224EWK'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:pass%40123@localhost:5432/flask_auth_db'

bcrypt = Bcrypt(app)
db.init_app(app)
migrate = Migrate(app, db)

app.register_blueprint(signup)

# Function to get user role from session
@app.context_processor
def get_user_role():
    return {'user_role': session.get('user_role')}

@app.route('/')
def home():
    return render_template('home.html')

def utc_to_ist(dt):
    if not dt:
        return "N/A"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=pytz.utc)
    ist = pytz.timezone("Asia/Kolkata")
    return dt.astimezone(ist).strftime('%Y-%m-%d %I:%M %p')


app.jinja_env.filters['utc_to_ist'] = utc_to_ist

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            ist = pytz.timezone('Asia/Kolkata')
            current_ist_time = datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(ist)

            if user.suspend_until:
                suspend_until_ist = user.suspend_until.replace(tzinfo=pytz.utc).astimezone(ist)
                if suspend_until_ist > current_ist_time:
                    suspend_reason = user.suspend_reason
                    flash(f'Your account has been suspended until {suspend_until_ist.strftime("%Y-%m-%d %I:%M %p")} IST for {suspend_reason}.', 'danger')
                    return render_template('login.html', form=form)
                
            session['user_id'] = user.id
            session['username'] = user.username
            session['user_role'] = user.role

            user.last_login = datetime.utcnow()
            db.session.commit()

            if user.role == 'job_seeker':   
                return redirect(url_for('dashboard.job_seeker_dashboard'))
            elif user.role == 'job_recruiter':
                return redirect(url_for('dashboard.recruiter_dashboard'))
            elif user.is_admin:
                return redirect(url_for('dashboard.admin_dashboard'))

            flash('Login Failed. Invalid role.', 'danger')
        else:
            flash('Login Failed. Check your email and password', 'danger')
    return render_template('login.html', form=form)


@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/terms-of-service')
def terms():
    return render_template('terms.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/privacy-policy')
def privacyPolicy():
    return render_template('privacypolicy.html')


def is_strong_password(password):
    if (len(password) < 8 or
        not re.search(r'[A-Z]', password) or
        not re.search(r'[a-z]', password) or
        not re.search(r'[0-9]', password) or
        not re.search(r'[!@#$%^&*(),.?":{}|<>]', password)):
        return False
    return True

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if not user:
            flash("User not found.", "danger")
            return redirect(url_for('login'))

        edit_mode = request.args.get('edit', 'false') == 'true'

        change_password = request.args.get('changePassword', 'false') == 'true'

        change_security = request.args.get('securityQues', 'false') == 'true'

        if request.method == 'POST':
            if change_password:
                current_password = request.form.get('current_password')
                new_password = request.form.get('new_password')
                confirm_password = request.form.get('confirm_password')

                if not bcrypt.check_password_hash(user.password, current_password):
                    flash("Current password is incorrect.", "danger")
                    return redirect(url_for('settings', changePassword='true'))

                if new_password != confirm_password:
                    flash("New passwords do not match.", "danger")
                    return redirect(url_for('settings', changePassword='true'))

                if new_password != confirm_password:
                    flash("New passwords do not match.", "danger")
                    return redirect(url_for('settings', changePassword='true'))

                if not is_strong_password(new_password):
                    flash("Password must be at least 8 characters long and include at least one uppercase letter, one lowercase letter, one digit, and one special symbol.", "danger")
                    return redirect(url_for('settings', changePassword='true'))

                user.password = bcrypt.generate_password_hash(new_password).decode('utf-8')
                db.session.commit()

                flash("Password updated successfully!", "success")
                return redirect(url_for('settings'))

            elif change_security:
                security_question = request.form.get('security_question')
                security_answer = request.form.get('security_answer')

                user.security_question = security_question
                user.security_answer = security_answer

                db.session.commit()

                flash("Security question updated successfully!", "success")
                return redirect(url_for('settings'))

            else:
                name = request.form.get('name')
                email = request.form.get('email')
                phone = request.form.get('phone')

                user.username = name
                user.email = email
                user.phone = phone

                db.session.commit()

                flash("Details updated successfully!", "success")
                return redirect(url_for('settings'))

        return render_template('settings.html', user_info=user, edit_mode=edit_mode, changePassword=change_password, change_security=change_security)

    flash("You must be logged in to access this page.", "danger")
    return redirect(url_for('login'))


s = URLSafeTimedSerializer(app.config['SECRET_KEY'])

@app.route('/resetpassword', methods=['GET', 'POST'])
def resetpassword():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()

        if user:
            token = s.dumps(user.email, salt='password-reset')
            reset_url = url_for('resetpassword_token', token=token, _external=True)
            email_body = f"Click the link below to reset your password:\n{reset_url}"

            if send_email(user.email, "Password Reset Request", email_body):
                flash("A password reset link has been sent to your email. You can close this window.", "info")
            else:
                flash("Error sending email. Try again later.", "danger")
        else:
            flash("Email not found.", "danger")

    return render_template('resetpassword.html')


@app.route('/resetpassword/<token>', methods=['GET', 'POST'])
def resetpassword_token(token):
    try:
        email = s.loads(token, salt='password-reset', max_age=3600)
    except:
        flash("Invalid or expired token.", "danger")
        return redirect(url_for('resetpassword'))

    user = User.query.filter_by(email=email).first()
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('resetpassword'))

    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if new_password != confirm_password:
            flash("Passwords do not match.", "danger")
        elif not is_strong_password(new_password):
            flash("Password must be at least 8 characters long and include at least one uppercase letter, one lowercase letter, one digit, and one special symbol.", "danger")
        else:
            user.password = bcrypt.generate_password_hash(new_password).decode('utf-8')
            db.session.commit()
            flash("Password reset successful. You can now log in.", "success")
            return redirect(url_for('login'))

    return render_template('resetpassword_form.html', token=token)


app.register_blueprint(dashboard)

app.register_blueprint(predictor)

def send_email(to_email, subject, body):
    sender_email = EMAIL_ADDRESS
    sender_password = LOGIN_PASSWORD

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = to_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.send_message(message)
        return True
    except Exception as e:
        print("Error sending email:", e)
        return False

@app.route('/delete_account', methods=['POST'])
def delete_account():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    if user:
        db.session.delete(user)
        db.session.commit()
        session.clear()
        flash("Your account has been deleted successfully.", "success")
        return redirect(url_for('login'))
    return redirect(url_for('settings'))


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
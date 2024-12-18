from flask import Flask, render_template, flash, url_for, redirect, session, request, jsonify
from models import db, User, JobProfile
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
from forms import LoginForm
from signup import signup 
from dashboard import dashboard
from predictor import predictor
import os

app = Flask (__name__)
app.config['SECRET_KEY'] = 'FDKJF224EWK'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:pass%40123@localhost:5432/flask_auth_db'

bcrypt = Bcrypt(app)
db.init_app(app)
migrate = Migrate(app, db)

with app.app_context(): 
    #db.create_all()
    # Check if the admin user already exists
    if not User.query.filter_by(email='admin@restack.com').first():
        hashed_password = bcrypt.generate_password_hash('admin').decode('utf-8')  # Hash the password
        admin_user = User(username='admin', email='admin@restack.com', password=hashed_password, is_admin=True, role='admin')  # Set the role as 'admin'
        db.session.add(admin_user)
        db.session.commit()


app.register_blueprint(signup)  # Register the signup blueprint

# Function to get user role from session
@app.context_processor
def get_user_role():
    return {'user_role': session.get('user_role')}  # Returns 'guest' if no role is set

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            session['user_id'] = user.id
            session['username'] = user.username
            session['user_role'] = user.role

            # Check user role and redirect accordingly
            if user.role == 'job_seeker':   
                return redirect(url_for('dashboard.job_seeker_dashboard'))  # Update to your job seeker dashboard route
            elif user.role == 'job_recruiter':
                return redirect(url_for('dashboard.recruiter_dashboard'))  # Update to your recruiter dashboard route
            elif user.is_admin:  # Assuming you have an is_admin attribute in your User model
                return redirect(url_for('dashboard.admin_dashboard'))  # Update to your admin dashboard route

            flash('Login Failed. Invalid role.', 'danger')
        else:
            flash('Login Failed. Check your email and password', 'danger')
    return render_template('login.html', form=form)


@app.route('/about')
def about():
    return render_template('about.html')

#Main admin, job seeker and job recruiter dashboards to see the data
app.register_blueprint(dashboard)

app.register_blueprint(predictor)

@app.route('/logout')
def logout():
    session.clear()  # Clears all session data at once
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
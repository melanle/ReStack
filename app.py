from flask import Flask, render_template, flash, url_for, redirect, session
from models import db, User
from flask_bcrypt import Bcrypt
from forms import RoleSelectForm, JobSeekerSignUpForm, JobRecruiterSignUpForm, LoginForm

app = Flask (__name__)
app.config['SECRET_KEY'] = 'FDKJF224EWK'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:pass%40123@localhost:5432/flask_auth_db'

bcrypt = Bcrypt()
db.init_app(app)
with app.app_context(): 
    db.create_all()

bcrypt.init_app(app)

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
            flash('You have been logged in!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Login Failed. Check your email and password', 'danger')
    return render_template('login.html', form = form)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    role_form = RoleSelectForm()
    if role_form.validate_on_submit():
        role = role_form.role.data
        if role == 'job_seeker':
            return redirect(url_for('signup_job_seeker'))
        elif role == 'job_recruiter':
            return redirect(url_for('signup_job_recruiter'))
    return render_template('select_role.html', form=role_form)

@app.route('/signup/job_seeker', methods=['GET', 'POST'])
def signup_job_seeker():
    form = JobSeekerSignUpForm()
    if form.validate_on_submit():
        # Hash the password and create a new Job Seeker user
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password, role='job_seeker')
        db.session.add(user)
        db.session.commit()
        
        # Flash success message and redirect to login or dashboard
        flash('Your account has been created as a Job Seeker!', 'success')
        return redirect(url_for('login'))
    return render_template('signup_job_seeker.html', form=form)

@app.route('/signup/job_recruiter', methods=['GET', 'POST'])
def signup_job_recruiter():
    form = JobRecruiterSignUpForm()
    if form.validate_on_submit():
        # Hash the password and create a new Job Recruiter user
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.organization_name.data, email=form.email.data, password=hashed_password, role='job_recruiter')
        db.session.add(user)
        db.session.commit()
        
        # Flash success message and redirect to login or dashboard
        flash('Your account has been created as a Job Recruiter!', 'success')
        return redirect(url_for('login'))
    return render_template('signup_job_recruiter.html', form=form)

# @app.route('/signup', methods = ['GET', 'POST'])
# def signup():
#     form = SignUpForm()
#     if form.validate_on_submit():
#         hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
#         user = User(
#             username=form.username.data,
#             email=form.email.data,
#             password=hashed_password,
#         )
#         db.session.add(user)
#         db.session.commit()
#         flash('Your account has been created!', 'success') #not using it for now
#         return redirect(url_for('login'))
#     return render_template('signup.html', form = form)

@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please login to access dashboard', 'warning')
        return redirect(url_for('login'))
    return render_template('dashboard.html')


@app.route('/logout')
def logout():
    if 'user_id' in session:
        session.pop('user_id')
        flash('You have been logged out.', 'success')
    else:
        flash('You were not logged in.', 'warning')  # Handle as appropriate
    
    if 'username' in session:
        session.pop('username')  # Pop username only if it exists
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
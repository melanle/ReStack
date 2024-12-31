from flask import Blueprint, render_template, redirect, url_for, flash
from forms import RoleSelectForm, JobSeekerSignUpForm, RecruiterSignUpForm
from models import db, User
from flask_bcrypt import Bcrypt

bcrypt = Bcrypt()
signup = Blueprint('signup', __name__, template_folder='templates')

@signup.route('/signup', methods=['GET', 'POST'])
def select_role():
    role_form = RoleSelectForm()
    if role_form.validate_on_submit():
        role = role_form.role.data
        if role == 'job_seeker':
            return redirect(url_for('signup.signup_job_seeker'))
        elif role == 'job_recruiter':
            return redirect(url_for('signup.signup_job_recruiter'))
    return render_template('select_role.html', form=role_form)

@signup.route('/signup/job_seeker', methods=['GET', 'POST'])
def signup_job_seeker():
    form = JobSeekerSignUpForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password, role='job_seeker')
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created as a Job Seeker!', 'success')
        return redirect(url_for('login'))
    return render_template('signup_job_seeker.html', form=form)

@signup.route('/signup/job_recruiter', methods=['GET', 'POST'])
def signup_job_recruiter():
    form = RecruiterSignUpForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.organization_name.data, email=form.email.data, password=hashed_password, role='job_recruiter')
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created as a Job Recruiter!', 'success')
        return redirect(url_for('login'))
    return render_template('signup_job_recruiter.html', form=form)
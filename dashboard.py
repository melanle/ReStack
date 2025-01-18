from flask import Blueprint, render_template, redirect, url_for, flash, session, request
from werkzeug.utils import secure_filename
from predictor import process_and_score
import os
from models import User, JobProfile, db, ResumeResults
dashboard = Blueprint('dashboard', __name__)


@dashboard.route('/admin_dashboard')
def admin_dashboard():
    # Check if user is logged in and has an admin role
    if 'user_id' in session and session.get('user_role') == 'admin':
        job_recruiters = User.query.filter_by(role="job_recruiter").all()
        job_seekers = User.query.filter_by(role="job_seeker").all()
        return render_template('admin_dashboard.html', job_recruiters = job_recruiters, job_seekers = job_seekers)
    else:
        flash('You do not have permission to access this page.', 'warning')
        return redirect(url_for('login'))

@dashboard.route('/job_profiles/<string:username>')
def view_job_profile(username):
    if session.get('user_role') == 'admin':
        recruiter = User.query.filter_by(username=username, role='job_recruiter').first()
        if recruiter:
            job_profiles = JobProfile.query.filter_by(recruiter_id=recruiter.id).all()
            return render_template('job_profiles.html', recruiter=recruiter, job_profiles=job_profiles)
        else:
            flash('No job recruiter found with the provided username.', 'danger')
            return redirect(url_for('dashboard.admin_dashboard'))
    else:
        flash('Please login with Admin Credentials in order to view this page', 'warning')
        return redirect(url_for('login'))


@dashboard.route('/job_seeker_dashboard')
def job_seeker_dashboard():
    if 'user_id' in session and session.get('user_role') == 'job_seeker':
        user_id = session['user_id']
        applications = db.session.query(
            JobProfile.job_title,
            JobProfile.job_description,
            ResumeResults.resume_name,
            ResumeResults.resume_path
        ).join(ResumeResults, JobProfile.id == ResumeResults.job_profile_id).filter(ResumeResults.user_id == user_id).all()
        
        return render_template('job_seeker_dashboard.html', applications=applications)
    else:
        flash('Please login as a Job Seeker to access the dashboard', 'warning')
        return redirect(url_for('login'))





@dashboard.route('/jobs', methods=['GET', 'POST'])
def jobs():
    search_query = request.args.get('q', '')  # Get the search query from the URL parameters
    query = db.session.query(
        JobProfile.id,
        JobProfile.job_title,
        JobProfile.job_description,
        JobProfile.created_at,
        User.username.label("recruiter_name")
    ).join(User, JobProfile.recruiter_id == User.id)
    
    # Filter the job profiles if a search query is provided
    if search_query:
        query = query.filter(
            JobProfile.job_title.ilike(f"%{search_query}%") | 
            JobProfile.job_description.ilike(f"%{search_query}%")
        )
    
    job_profiles = query.all()
    return render_template('jobs.html', jobs=job_profiles, search_query=search_query)


@dashboard.route('/apply/<int:job_id>', methods=['GET', 'POST'])
def apply(job_id):
    job = db.session.query(
        JobProfile.id,  # Include the job ID
        JobProfile.job_title,
        JobProfile.job_description,
        User.username.label("recruiter_name")
    ).join(User, JobProfile.recruiter_id == User.id).filter(JobProfile.id == job_id).first()

    if request.method == 'POST':
        resume = request.files['resume']
        if resume and (resume.filename.endswith('.pdf') or resume.filename.endswith('.docx')):
            filename = secure_filename(resume.filename)
            file_path = os.path.join('uploads', filename)
            resume.save(file_path)
            score = process_and_score(file_path, job.job_description)

            # Save resume details to the database
            new_resume = ResumeResults(
                resume_name=filename,
                resume_path=file_path,
                score=score,
                job_profile_id=job.id,
                user_id=session['user_id']  # Save the job seeker ID
            )
            db.session.add(new_resume)
            db.session.commit()
            
            flash('Resume uploaded and submitted successfully!', 'success')
            return redirect(url_for('dashboard.job_seeker_dashboard'))
        else:
            flash('Incorrect file format! Please upload only PDF or DOCX files.', 'danger')

    return render_template('apply.html', job=job)


 


    
@dashboard.route('/recruiter_dashboard')
def recruiter_dashboard():
    if 'user_id' in session and session.get('user_role') == 'job_recruiter':
        recruiter = User.query.get(session['user_id'])
        job_profiles = recruiter.job_profiles
        return render_template('recruiter_dashboard.html', job_profiles=job_profiles)
    else:
        flash('Please log in as a Job Recruiter to access the dashboard.', 'warning')
        return redirect(url_for('login'))
    
#Adding a Job Profile to the Recruiter's Dashboard
@dashboard.route('/add_job_profile', methods=['POST'])
def add_job_profile():
    if 'user_id' in session and session.get('user_role') == 'job_recruiter':
        job_title = request.form.get('job_title')
        job_description = request.form.get('job_description')
        
        new_job = JobProfile(
            job_title=job_title,
            job_description=job_description,
            recruiter_id=session['user_id']
        )
        db.session.add(new_job)
        db.session.commit()
        flash('Job profile created successfully.', 'success')
        return redirect(url_for('dashboard.recruiter_dashboard'))
    return redirect(url_for('login'))

#Editing The Job Profile
@dashboard.route('/edit_job_profile/<int:job_id>', methods=['GET', 'POST'])
def edit_job_profile(job_id):
    job_profile = JobProfile.query.get_or_404(job_id)
    if 'user_id' in session and job_profile.recruiter_id == session['user_id']:
        if request.method == 'POST':
            job_profile.job_title = request.form['job_title']
            job_profile.job_description = request.form['job_description']
            db.session.commit()
            flash('Job profile updated.', 'success')
            return redirect(url_for('dashboard.recruiter_dashboard'))
    return redirect(url_for('login'))

#Deleting the Job Profile
@dashboard.route('/delete_job_profile/<int:job_id>', methods=['POST'])
def delete_job_profile(job_id):
    job_profile = JobProfile.query.get_or_404(job_id)
    if 'user_id' in session and job_profile.recruiter_id == session['user_id']:
        db.session.delete(job_profile)
        db.session.commit()
        flash('Job profile deleted.', 'success')
        return redirect(url_for('dashboard.recruiter_dashboard'))
    return redirect(url_for('login'))
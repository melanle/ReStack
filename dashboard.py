from flask import Blueprint, render_template, redirect, url_for, flash, session, request
from datetime import datetime, timedelta
import pytz
from werkzeug.utils import secure_filename
from predictor import process_and_score
from sqlalchemy.sql import func
import os
from models import User, JobProfile, db, ResumeResults, JobApplication
from sqlalchemy import delete
dashboard = Blueprint('dashboard', __name__)


UPLOAD_FOLDER = './uploads'
@dashboard.route('/admin_dashboard')
def admin_dashboard():
    if 'user_id' in session and session.get('user_role') == 'admin':
        ist = pytz.timezone('Asia/Kolkata')
        current_time = datetime.now(ist)

        job_recruiters = User.query.filter_by(role="job_recruiter").all()
        job_seekers = User.query.filter_by(role="job_seeker").all()
        total_jobs_posted = JobProfile.query.count()
        total_resumes_uploaded = ResumeResults.query.count()
        total_users_suspended = User.query.filter_by(is_suspended=True).count()

        users = job_seekers + job_recruiters
        for user in users:
            if user.suspend_until:
                if user.suspend_until.tzinfo is None:
                    utc_time = pytz.utc.localize(user.suspend_until)
                else:
                    utc_time = user.suspend_until.astimezone(pytz.utc)
                suspend_until_ist = utc_time.astimezone(ist)

                if suspend_until_ist < current_time:
                    user.is_suspended = False
                    user.suspend_until = None
                    user.suspend_reason = None
                    db.session.commit()
                else:
                    user.suspend_until = suspend_until_ist

        total_users = len(users)
        suspended = len([u for u in users if u.is_suspended])
        suspended_counts = {
            "Active": total_users - suspended,
            "Suspended": suspended
        }

        reason_counts = db.session.query(User.suspend_reason, func.count(User.id))\
            .filter(User.is_suspended == True, User.suspend_reason != None)\
            .group_by(User.suspend_reason).all()

        suspension_reasons = {reason: count for reason, count in reason_counts}

        job_seekers_count = len(job_seekers)
        job_recruiters_count = len(job_recruiters)

        company_job_counts = db.session.query(User.username, func.count(JobProfile.id))\
            .join(JobProfile, User.id == JobProfile.recruiter_id)\
            .filter(User.role == "job_recruiter")\
            .group_by(User.username)\
            .order_by(func.count(JobProfile.id).desc())\
            .limit(5).all()

        companies = [username[0] for username in company_job_counts]
        job_counts = [username[1] for username in company_job_counts]

        top_applicants = db.session.query(User.username, func.count(JobApplication.id))\
            .join(JobApplication, User.id == JobApplication.user_id)\
            .filter(User.role == "job_seeker")\
            .group_by(User.username)\
            .order_by(func.count(JobApplication.id).desc())\
            .limit(5).all()

        applicant_names = [applicant[0] for applicant in top_applicants]
        application_counts = [applicant[1] for applicant in top_applicants]

        return render_template(
            'admin_dashboard.html',
            job_recruiters=job_recruiters,
            job_seekers=job_seekers,
            job_recruiters_count=job_recruiters_count,
            job_seekers_count=job_seekers_count,
            companies=companies,
            job_counts=job_counts,
            applicant_names=applicant_names,
            application_counts=application_counts,
            current_time=current_time,
            users=users,
            total_jobs_posted=total_jobs_posted,
            total_resumes_uploaded=total_resumes_uploaded,
            total_users_suspended=total_users_suspended,
            suspended_counts=suspended_counts,
            suspension_reasons=suspension_reasons
        )
    else:
        flash('You do not have permission to access this page.', 'warning')
        return redirect(url_for('login'))


@dashboard.route('/suspend_user', methods=['POST'])
def suspend_user():
    user_id = request.form['user_id']
    role = request.form['role']
    days = int(request.form['suspend_days'])
    hours = int(request.form['suspend_hours'])
    minutes = int(request.form['suspend_minutes'])
    reason = request.form.get('reason')
    custom_reason = request.form.get('custom_reason')
    
    suspend_until_utc = datetime.utcnow() + timedelta(days=days, hours=hours, minutes=minutes)

    full_reason = custom_reason if reason == "Other" else reason

    user = User.query.get(user_id)
    if user and user.role == role:
        user.is_suspended = True
        user.suspend_until = suspend_until_utc
        user.suspend_reason = full_reason
        db.session.commit()
        flash("User suspended successfully", "success")

    return redirect(url_for("dashboard.admin_dashboard"))


@dashboard.route('/unsuspend_user', methods=['POST'])
def unsuspend_user():
    user_id = request.form.get('user_id')
    if user_id:
        user = User.query.get(user_id)
        if user:
            user.is_suspended = False
            user.suspend_until = datetime.utcnow()
            db.session.commit()
            flash(f"{user.username} has been unsuspended.", "success")
        else:
            flash("User not found.", "danger")
    else:
        flash("Invalid request.", "danger")

    return redirect(url_for('dashboard.admin_dashboard'))


@dashboard.route('/admin_dashboard/recruiters')
def recruiters():
    if 'user_id' in session and session.get('user_role') == 'admin':
        recruiters = User.query.filter_by(role='job_recruiter').all()
        return render_template('recruiters.html', recruiters=recruiters)
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
            ResumeResults.resume_path,
            User.username.label('recruiter_name'),
            ResumeResults.status,
            ResumeResults.id.label('resume_id')
        ).join(ResumeResults, JobProfile.id == ResumeResults.job_profile_id)\
        .join(User, JobProfile.recruiter_id == User.id)\
        .join(JobApplication, (JobApplication.job_profile_id == JobProfile.id) & 
                              (JobApplication.user_id == ResumeResults.user_id))\
        .filter(ResumeResults.user_id == user_id)\
        .all()

        return render_template('job_seeker_dashboard.html', applications=applications)
    else:
        flash('Please login as a Job Seeker to access the dashboard', 'warning')
        return redirect(url_for('login'))
    
@dashboard.route('/delete_application/<int:resume_id>', methods=['POST'])
def delete_application(resume_id):
    resume = ResumeResults.query.get_or_404(resume_id)

    try:
        if os.path.exists(resume.resume_path):
            os.remove(resume.resume_path)

        db.session.delete(resume)

        job_application = JobApplication.query.filter_by(
            job_profile_id=resume.job_profile_id,
            user_id=session['user_id']
        ).first()

        if job_application:
            db.session.delete(job_application)

        db.session.commit()
        flash("Application deleted successfully!", "success")
    except Exception as e:
        flash(f"Error deleting application: {str(e)}", "danger")

    return redirect(url_for('dashboard.job_seeker_dashboard'))


@dashboard.route('/jobs', methods=['GET'])
def jobs():
    if 'user_id' in session and session.get('user_role') == 'job_seeker':
        user_id = session['user_id']
        search_query = request.args.get('q', '')
        
        query = db.session.query(
            JobProfile.id,
            JobProfile.job_title,
            JobProfile.job_description,
            JobProfile.created_at,
            User.username.label("recruiter_name")
        ).join(User, JobProfile.recruiter_id == User.id)\
        .outerjoin(JobApplication, (JobApplication.job_profile_id == JobProfile.id) & 
                                     (JobApplication.user_id == user_id))\
        .filter(JobApplication.id.is_(None))

        if search_query:
            query = query.filter(
                JobProfile.job_title.ilike(f"%{search_query}%") | 
                JobProfile.job_description.ilike(f"%{search_query}%")
            )
        
        job_profiles = query.all()
        return render_template('jobs.html', jobs=job_profiles, search_query=search_query)
    else:
        flash('Please log in as a Job Seeker to view available jobs.', 'warning')
        return redirect(url_for('login'))


@dashboard.route('/apply/<int:job_id>', methods=['GET', 'POST'])
def apply(job_id):
    job = db.session.query(
        JobProfile.id,
        JobProfile.job_title,
        JobProfile.job_description,
        User.username.label("recruiter_name")
    ).join(User, JobProfile.recruiter_id == User.id).filter(JobProfile.id == job_id).first()

    if request.method == 'POST':
        resume = request.files['resume']
        if resume and (resume.filename.endswith('.pdf') or resume.filename.endswith('.docx')):
            filename = secure_filename(resume.filename)
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            resume.save(file_path)
            score = process_and_score(file_path, job.job_description)

            new_resume = ResumeResults(
                resume_name=filename,
                resume_path=file_path,
                score=score,
                job_profile_id=job.id,
                user_id=session['user_id']
            )
            db.session.add(new_resume)

            new_application = JobApplication(
                job_profile_id=job.id,
                user_id=session['user_id']
            )
            db.session.add(new_application)
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


@dashboard.route('/delete_job_profile/<int:job_id>', methods=['POST'])
def delete_job_profile(job_id):
    job_profile = JobProfile.query.get_or_404(job_id)

    if 'user_id' in session and job_profile.recruiter_id == session['user_id']:
        db.session.execute(delete(JobApplication).where(JobApplication.job_profile_id == job_id))
        db.session.delete(job_profile)
        db.session.commit()

        flash('Job profile and associated applications deleted.', 'success')
        return redirect(url_for('dashboard.recruiter_dashboard'))

    return redirect(url_for('login'))
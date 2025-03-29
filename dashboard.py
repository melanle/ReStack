from flask import Blueprint, render_template, redirect, url_for, flash, session, request, jsonify
from werkzeug.utils import secure_filename
from predictor import process_and_score
from sqlalchemy.sql import func
import os
from models import User, JobProfile, db, ResumeResults, JobApplication
dashboard = Blueprint('dashboard', __name__)


UPLOAD_FOLDER = './uploads'
@dashboard.route('/admin_dashboard')
def admin_dashboard():
    if 'user_id' in session and session.get('user_role') == 'admin':
        job_recruiters = User.query.filter_by(role="job_recruiter").all()
        job_seekers = User.query.filter_by(role="job_seeker").all()

        # Pie Chart Data (User Bifurcation)
        job_seekers_count = len(job_seekers)
        job_recruiters_count = len(job_recruiters)

        # Bar Graph Data (Top 5 Companies with Most Job Posts)
        company_job_counts = db.session.query(User.username, func.count(JobProfile.id))\
            .join(JobProfile, User.id == JobProfile.recruiter_id)\
            .filter(User.role == "job_recruiter")\
            .group_by(User.username)\
            .order_by(func.count(JobProfile.id).desc())\
            .limit(5).all()

        companies = [username[0] for username in company_job_counts]
        job_counts = [username[1] for username in company_job_counts]

        # Top 5 Active Job Seekers (Most Applications Submitted)
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
            application_counts=application_counts
        )
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
        # Delete the file from the file system
        if os.path.exists(resume.resume_path):
            os.remove(resume.resume_path)

        # Remove the record from the ResumeResults table
        db.session.delete(resume)

        # Remove the associated entry in the JobApplication table
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

    #     return jsonify({"status": "success", "message": "Resume deleted successfully!"})
    # except Exception as e:
    #     return jsonify({"status": "error", "message": f"Error deleting resume: {str(e)}"}), 500





@dashboard.route('/jobs', methods=['GET'])
def jobs():
    if 'user_id' in session and session.get('user_role') == 'job_seeker':
        user_id = session['user_id']  # Get the logged-in user's ID
        search_query = request.args.get('q', '')  # Get the search query from the URL parameters
        
        # Query to get all job profiles excluding jobs currently applied for by the user
        query = db.session.query(
            JobProfile.id,
            JobProfile.job_title,
            JobProfile.job_description,
            JobProfile.created_at,
            User.username.label("recruiter_name")
        ).join(User, JobProfile.recruiter_id == User.id)\
        .outerjoin(JobApplication, (JobApplication.job_profile_id == JobProfile.id) & 
                                     (JobApplication.user_id == user_id))\
        .filter(JobApplication.id.is_(None))  # Exclude jobs the user has applied for

        # Filter the job profiles if a search query is provided
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



# @dashboard.route('/jobs', methods=['GET', 'POST'])
# def jobs():
#     search_query = request.args.get('q', '')  # Get the search query from the URL parameters
#     query = db.session.query(
#         JobProfile.id,
#         JobProfile.job_title,
#         JobProfile.job_description,
#         JobProfile.created_at,
#         User.username.label("recruiter_name")
#     ).join(User, JobProfile.recruiter_id == User.id)
    
#     # Filter the job profiles if a search query is provided
#     if search_query:
#         query = query.filter(
#             JobProfile.job_title.ilike(f"%{search_query}%") | 
#             JobProfile.job_description.ilike(f"%{search_query}%")
#         )
    
#     job_profiles = query.all()
#     return render_template('jobs.html', jobs=job_profiles, search_query=search_query)


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
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            resume.save(file_path)
            score = process_and_score(file_path, job.job_description)

            # Save resume details to the database with consistent path
            new_resume = ResumeResults(
                resume_name=filename,
                resume_path=file_path,  # Use file_path as in the predict route
                score=score,
                job_profile_id=job.id,
                user_id=session['user_id']  # Save the job seeker ID
            )
            db.session.add(new_resume)
            
            # Create an entry in job_applications
            new_application = JobApplication(
                job_profile_id=job.id,
                user_id=session['user_id']  # Save the job seeker ID
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
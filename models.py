from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

db = SQLAlchemy()

#Users Model
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(200), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(10), unique=True)
    password = db.Column(db.String(60), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    security_question = db.Column(db.String(255), nullable=True) 
    security_answer = db.Column(db.String(255), nullable=True)

    #Creating a relationship to JobProfile (for recruiters)
    job_profiles = db.relationship('JobProfile', backref='recruiter', lazy=True)


#Job Profile Model
class JobProfile(db.Model):
    __tablename__ = 'job_profiles'
    id = db.Column(db.Integer, primary_key=True)
    job_title = db.Column(db.String(200), nullable=False)
    job_description = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    #Foreign Key to link to the User(recruiter)
    recruiter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    #Relationship with ResumeResults
    resumes = db.relationship('ResumeResults', back_populates='job_profile', cascade="all, delete-orphan")

#Resume Results Model
class ResumeResults(db.Model):
    __tablename__ = 'resume_results'
    
    id = db.Column(db.Integer, primary_key=True)
    resume_name = db.Column(db.String(255), nullable=False)
    score = db.Column(db.Float, nullable=False)  # Store score as a float
    resume_path = db.Column(db.String(255), nullable=False)  # Path to the resume file
    job_profile_id = db.Column(db.Integer, db.ForeignKey('job_profiles.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with the JobProfile model
    job_profile = db.relationship('JobProfile', back_populates='resumes')
    user = db.relationship('User', backref='resumes')  # Add this line

    def __repr__(self):
        return f"<ResumeResults {self.resume_name}, {self.score}>"

# Job Applications Model
class JobApplication(db.Model):
    __tablename__ = 'job_applications'
    id = db.Column(db.Integer, primary_key=True)
    job_profile_id = db.Column(db.Integer, db.ForeignKey('job_profiles.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='Pending')

    # Relationships
    job_profile = db.relationship('JobProfile', backref='job_applications')
    user = db.relationship('User', backref='job_applications')

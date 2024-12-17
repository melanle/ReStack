from flask import Blueprint, request, render_template, jsonify, session, flash, redirect, url_for, send_file
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import os
import google.generativeai as genai
from PyPDF2 import PdfReader
from docx import Document
from models import User, JobProfile, ResumeResults, db

# Create Blueprint
predictor = Blueprint('predictor', __name__)
UPLOAD_FOLDER = './uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

load_dotenv() #Loading env to activate API Key

# Configure Gemini API
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))

# Create the Gemini model
generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
    model_name="gemini-2.0-flash-exp",
    generation_config=generation_config,
)

#Extracting Text from pdf
def extract_text_from_pdf(file_path):
    try:
        reader = PdfReader(file_path)
        return " ".join(page.extract_text() for page in reader.pages)
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return ""

#Extracting Text from docx
def extract_text_from_docx(file_path):
    try:
        doc = Document(file_path)
        return " ".join(paragraph.text for paragraph in doc.paragraphs)
    except Exception as e:
        print(f"Error extracting text from DOCX: {e}")
        return ""

def process_and_score(resume_path, job_description):
    # Extract resume text
    if resume_path.endswith(".pdf"):
        resume_text = extract_text_from_pdf(resume_path)
    elif resume_path.endswith(".docx"):
        resume_text = extract_text_from_docx(resume_path)
    else:
        raise ValueError("Unsupported file format. Please upload a PDF or DOCX.")

    user = User.query.get(session['user_id'])
    if user.role == 'job_seeker':
        # Create prompt for Gemini
        prompt = f"""
        You are a scoring system designed to strictly evaluate resumes against a given job description.  
        Here is the job description:  {job_description}  
        Here is the resume:  {resume_text}  
        Evaluate the resume based solely on its relevance and quality in meeting the job requirements. Provide a single, overall score out of 100. Be objective and rigorous in your evaluation. Do not provide any explanation, details, or additional comments. Your response should only be the numerical score.
        """
    elif user.role == 'job_recruiter':
        prompt = f"""
        You are a scoring system designed to strictly evaluate resumes against a given job description.  
        Here is the job description:  {job_description}  
        Here is the resume:  {resume_text}  
        Evaluate the resume based solely on its relevance and quality in meeting the job requirements. Provide a single, overall score out of 100. Be objective and rigorous in your evaluation. Do not provide any explanation, details, or additional comments. Your response should only be the numerical score.
        """
    # Send prompt to Gemini
    chat_session = model.start_chat(history=[])
    response = chat_session.send_message(prompt)
    return float(response.text)

# Flask routes
@predictor.route('/predict', methods = ['GET', 'POST'])
def predict():
    error = None
    score = None

    if request.method == 'POST':
        resume = request.files['resume']
        job_description = request.form['job_description']

        # Save the uploaded file
        filename = secure_filename(resume.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        resume.save(file_path)

        try:
            # Process and score the resume
            score_response = process_and_score(file_path, job_description)
            score = score_response  # Store the score
        except Exception as e:
            error = str(e)  # Store the error message

    return render_template('predict.html', error=error, score=score)


@predictor.route('/view_resumes/<int:job_id>', methods=['GET', 'POST'])
def view_resumes(job_id):
    # Fetch the job profile from the database
    job = JobProfile.query.get_or_404(job_id)

    if request.method == 'POST':
        # Ensure files are present in the request
        if 'resumes' not in request.files:
            flash('No resumes uploaded!', 'danger')
            return jsonify({"status": "danger", "message": "No resumes uploaded!"})

        uploaded_resumes = request.files.getlist('resumes')

        # Validate and save each uploaded resume
        for resume in uploaded_resumes:
            # Check if the resume has a valid file extension (PDF or DOCX)
            if resume and (resume.filename.endswith('.pdf') or resume.filename.endswith('.docx')):
                filename = secure_filename(resume.filename)
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                resume.save(file_path)

                try:
                    # Process and score each resume
                    score = process_and_score(file_path, job.job_description)

                    # Save resume details to the database
                    new_resume = ResumeResults(
                        resume_name=filename,
                        score=score,
                        resume_path=file_path,
                        job_profile_id=job.id
                    )
                    db.session.add(new_resume)
                    db.session.commit()

                except Exception as e:
                    flash(f"Error processing resume '{filename}': {str(e)}", 'danger')
                    return jsonify({"status": "danger", "message": f"Error processing resume '{filename}': {str(e)}"})
            else:
                flash('Incorrect file format! Please upload only PDF or DOCX files.', 'danger')
                return jsonify({"status": "danger", "message": "Incorrect file format! Please upload only PDF or DOCX files."})

        # Instead of redirecting, return the updated resumes as JSON
        resumes = ResumeResults.query.filter_by(job_profile_id=job_id).all()
        resume_rows = ""
        for resume in resumes:
            resume_rows += f"""
            <tr id="resumeRow-{resume.id}">
                <td>{resume.resume_name}</td>
                <td>
                    <span class="badge 
                        {'badge-green' if resume.score >= 80 else 'badge-orange' if resume.score >= 50 else 'badge-red'}">
                        {resume.score}% 
                    </span>
                </td>
                <td>
                    <a href="{url_for('predictor.viewres', resume_id=resume.id)}" class="btn btn-sm btn-info" target="_blank">View</a>
                    <form method="POST" action="{url_for('predictor.delete_resume', resume_id=resume.id)}" style="display:inline;">
                        <button type="submit" class="btn btn-sm btn-danger">Delete</button>
                    </form>
                </td>
            </tr>
            """

        # Return success response with a proper message
        return jsonify({
            "status": "success",
            "message": "Resumes uploaded and processed successfully!",
            "rows": resume_rows
        })

    # Fetch resumes associated with the job profile
    resumes = ResumeResults.query.filter_by(job_profile_id=job_id).all()

    # Pass the job and resumes to the template
    return render_template('view_resumes.html', job=job, resumes=resumes)



@predictor.route('/viewres/<int:resume_id>', methods=['GET'])
def viewres(resume_id):
    # Fetch the resume from the database using the resume_id
    resume = ResumeResults.query.get_or_404(resume_id)

    # Ensure the file exists
    if not os.path.exists(resume.resume_path):
        return "Resume file not found!", 404

    # Serve the file in the browser (it will open in a new tab)
    return send_file(resume.resume_path, as_attachment=False)


@predictor.route('/delete_resume/<int:resume_id>', methods=['POST'])
def delete_resume(resume_id):
    resume = ResumeResults.query.get_or_404(resume_id)

    try:
        # Delete the file from the file system
        if os.path.exists(resume.resume_path):
            os.remove(resume.resume_path)

        # Remove the record from the database
        db.session.delete(resume)
        db.session.commit()

        flash("Resume deleted successfully!", "success")
    except Exception as e:
        flash(f"Error deleting resume: {str(e)}", "danger")

    return redirect(url_for('predictor.view_resumes', job_id=resume.job_profile_id))



@predictor.route('/uploadres', methods=['POST'])
def uploadres():
    try:
        job_id = request.form['job_id']
        job = JobProfile.query.get(job_id)

        if not job:
            return jsonify({"error": "Job profile not found.", "results": []})

        uploaded_resumes = request.files.getlist('resumes')
        results = []

        for resume in uploaded_resumes:
            filename = secure_filename(resume.filename)
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            resume.save(file_path)

            try:
                job_description = job.job_description
                score = process_and_score(file_path, job_description)

                resume_result = ResumeResults(
                    resume_name=filename,
                    score=score,
                    resume_path=file_path,
                    job_profile_id=job.id
                )

                db.session.add(resume_result)
                db.session.commit()

                results.append({
                    'candidate_name': filename,
                    'score': score
                })
            except Exception as e:
                return jsonify({"error": str(e), "results": []})

        return jsonify({"error": None, "results": results})
    except Exception as e:
        return jsonify({"error": str(e), "results": []})
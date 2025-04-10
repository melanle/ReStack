from flask import Blueprint, request, render_template, jsonify, session, flash, redirect, url_for, send_file
import markdown
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import os
import google.generativeai as genai
from PyPDF2 import PdfReader
from docx import Document
from models import User, JobProfile, ResumeResults, db

predictor = Blueprint('predictor', __name__)
UPLOAD_FOLDER = './uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


load_dotenv() #Loading env to activate API Key
base_model = "models/gemini-1.5-flash-001-tuning"

genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))

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

def process_and_score(resume_path, job_description, get_recommendations=False):
    if resume_path.endswith(".pdf"):
        resume_text = extract_text_from_pdf(resume_path)
    elif resume_path.endswith(".docx"):
        resume_text = extract_text_from_docx(resume_path)
    else:
        raise ValueError("Unsupported file format. Please upload a PDF or DOCX.")

    job_description = str(job_description)
    resume_text = str(resume_text)

    if get_recommendations:
        recommendation_prompt = f"""
        You are a scoring and recommendation system designed to strictly evaluate my resume.
        Based on the job description: {job_description} and the resume text: {resume_text},
        evaluate the resume based solely on its relevance and quality in meeting the job requirements. 
        Be objective and rigorous in your evaluation. Provide Suggestions on what could be added or improved in the resume
        to make it better suited for the job. Provide detailed and actionable recommendations on the resume's structure, content, or skills under 500 words.
        Make sure every section starts from a new line.
        Generate an evaluation report in the following format:
        **Score:** [Provide a score out of 100]\n\n
        **Strengths:**</bold>\n\n
        • [List strengths as bullet points]\n\n 
        • [Each point should be concise]\n\n
        **Weaknesses:**\n
        • [List weaknesses as bullet points]\n\n
        • [Each point should be direct]\n\n
        **Suggestions:**\n
        • [Provide actionable suggestions]\n\n
        • [Ensure each suggestion is relevant]\n\n

        Maintain this exact formatting, ensuring **double line breaks** between sections and *single line break after every bullet point.*

        """
        chat_session = model.start_chat(history=[])
        recommendation_response = chat_session.send_message(str(recommendation_prompt))
        response_text = recommendation_response.text
        markdown_output = markdown.markdown(response_text)
        return markdown_output

    else:    
        prompt = f"""
        You are a scoring system designed to strictly evaluate resumes against a given job description.
        Here is the job description:  {job_description}
        Here is the resume:  {resume_text}
        Evaluate the resume based solely on its relevance and quality in meeting the job requirements. Provide a single, overall score out of 100. Be objective and rigorous in your evaluation. Do not provide any explanation, details, or additional comments. Your response should only be the numerical score.
        """
        chat_session = model.start_chat(history=[])
        response = chat_session.send_message(prompt)
        return float(response.text)


@predictor.route('/predict', methods=['GET', 'POST'])
def predict():
    user = User.query.get(session['user_id'])
    if user.role != 'job_seeker':
        flash('You must be a job seeker to view this page.', 'danger')
        return redirect(url_for('home'))

    error = None
    score = None
    recommendations = None

    if request.method == 'POST':
        resume = request.files['resume']
        job_description = request.form['job_description']
        get_recommendations = request.form.get('get_recommendations', False)  # Flag to get recommendations

        filename = secure_filename(resume.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        resume.save(file_path)

        try:
            score_response = process_and_score(file_path, job_description, get_recommendations=get_recommendations)
            score = score_response if not get_recommendations else None 
            recommendations = score_response if get_recommendations else None
        except Exception as e:
            error = str(e)

    return render_template('predict.html', error=error, score=score, recommendations=recommendations)


@predictor.route('/view_resumes/<int:job_id>', methods=['GET', 'POST'])
def view_resumes(job_id):
    job = JobProfile.query.get_or_404(job_id)

    if request.method == 'POST':

        # If uploading resumes
        if 'resumes' in request.files:
            uploaded_resumes = request.files.getlist('resumes')

            for resume in uploaded_resumes:
                if resume and (resume.filename.endswith('.pdf') or resume.filename.endswith('.docx')):
                    filename = secure_filename(resume.filename)
                    file_path = os.path.join(UPLOAD_FOLDER, filename)
                    resume.save(file_path)

                    try:
                        score = process_and_score(file_path, job.job_description)

                        new_resume = ResumeResults(
                            resume_name=filename,
                            score=score,
                            resume_path=file_path,
                            job_profile_id=job.id
                        )
                        db.session.add(new_resume)
                        db.session.commit()

                    except Exception as e:
                        return jsonify({"status": "danger", "message": f"Error processing resume '{filename}': {str(e)}"})
                else:
                    return jsonify({"status": "danger", "message": "Incorrect file format! Please upload only PDF or DOCX files."})

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

            return jsonify({
                "status": "success",
                "message": "Resumes uploaded and processed successfully!",
                "rows": resume_rows
            })

        # If neither action triggered
        return jsonify({"status": "danger", "message": "Invalid request or missing data."}), 400

    # GET request
    resumes = ResumeResults.query.filter_by(job_profile_id=job_id).all()
    resumes = sorted(resumes, key=lambda r: r.score, reverse=True)

    return render_template('view_resumes.html', job=job, resumes=resumes)

@predictor.route('/update_status/<int:resume_id>', methods=['POST'])
def update_status(resume_id):
    # Validate that the user is a recruiter
    if session.get('user_role') != 'job_recruiter':
        return jsonify({"status": "error", "message": "Permission denied"}), 403

    # Retrieve the new status from the AJAX request
    new_status = request.json.get('status')
    if new_status not in ['Pending', 'In Touch', 'Selected', 'Not Selected']:
        return jsonify({"status": "error", "message": "Invalid status"}), 400

    # Update the resume in the database
    resume = ResumeResults.query.get_or_404(resume_id)
    resume.status = new_status
    db.session.commit()

    return jsonify({"status": "success", "message": "Status updated successfully!"})


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
from flask import Flask, render_template, flash, url_for, redirect, session, request
from models import db, User
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
from forms import LoginForm
from signup import signup 
from dashboard import dashboard
from predictor import predictor

app = Flask(__name__)
app.config['SECRET_KEY'] = 'FDKJF224EWK'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:pass%40123@localhost:5432/flask_auth_db'

bcrypt = Bcrypt(app)
db.init_app(app)
migrate = Migrate(app, db)

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

@app.route('/terms-of-service')
def terms():
    return render_template('terms.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/privacy-policy')
def privacyPolicy():
    return render_template('privacypolicy.html')


@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user_id' in session:
        # Fetch the logged-in user from the database
        user = User.query.get(session['user_id'])
        if not user:
            flash("User not found.", "danger")
            return redirect(url_for('login'))

        # Flag to toggle edit mode
        edit_mode = request.args.get('edit', 'false') == 'true'

        # Flag to toggle password change mode
        change_password = request.args.get('changePassword', 'false') == 'true'

        # Flag to toggle security question change mode
        change_security = request.args.get('securityQues', 'false') == 'true'

        if request.method == 'POST':
            if change_password:
                # Handle password change
                current_password = request.form.get('current_password')
                new_password = request.form.get('new_password')
                confirm_password = request.form.get('confirm_password')

                # Validate current password using bcrypt's check_password_hash
                if not bcrypt.check_password_hash(user.password, current_password):
                    flash("Current password is incorrect.", "danger")
                    return redirect(url_for('settings', changePassword='true'))

                # Check if new passwords match
                if new_password != confirm_password:
                    flash("New passwords do not match.", "danger")
                    return redirect(url_for('settings', changePassword='true'))

                # Update password (hash the new password before saving)
                user.password = bcrypt.generate_password_hash(new_password).decode('utf-8')
                db.session.commit()

                flash("Password updated successfully!", "success")
                return redirect(url_for('settings'))

            elif change_security:
                # Handle security question update
                security_question = request.form.get('security_question')
                security_answer = request.form.get('security_answer')

                # Update security question and answer
                user.security_question = security_question
                user.security_answer = security_answer

                db.session.commit()

                flash("Security question updated successfully!", "success")
                return redirect(url_for('settings'))

            else:
                # Handle general settings update
                name = request.form.get('name')
                email = request.form.get('email')
                phone = request.form.get('phone')

                # Update user details
                user.username = name
                user.email = email
                user.phone = phone  # Assuming you added a phone field in the User model

                # Commit changes to the database
                db.session.commit()

                flash("Details updated successfully!", "success")
                return redirect(url_for('settings'))

        # Pass the user data and flags to the template
        return render_template('settings.html', user_info=user, edit_mode=edit_mode, changePassword=change_password, change_security=change_security)

    flash("You must be logged in to access this page.", "danger")
    return redirect(url_for('login'))


@app.route('/resetpassword', methods=['GET', 'POST'])
def resetpassword():
    user = None
    reset_password_mode = False
    security_check_mode = False

    if request.method == 'POST':
        # Check which form was submitted
        if 'username_email' in request.form:
            username_email = request.form['username_email']
            user = User.query.filter((User.username == username_email) | (User.email == username_email)).first()

            if not user:
                flash("Invalid user. Please try again.", 'danger')
                return redirect(url_for('resetpassword'))  # Redirect to the same page

            flash(f"Security Question: {user.security_question}", 'info')
            return render_template('resetpassword.html', user=user, security_check_mode=True)

        elif 'security_answer' in request.form:
            user_id = request.form['user_id']
            security_answer = request.form['security_answer']
            user = User.query.get(user_id)

            if not user or user.security_answer.lower() != security_answer.lower():
                flash("Incorrect answer to the security question. Please try again.", 'danger')
                return redirect(url_for('resetpassword'))

            flash("Security answer verified. Please enter your new password.", 'success')
            return render_template('resetpassword.html', user=user, reset_password_mode=True)

        elif 'new_password' in request.form:
            user_id = request.form['user_id']
            new_password = request.form['new_password']
            confirm_password = request.form['confirm_password']

            if new_password != confirm_password:
                flash("Passwords do not match. Please try again.", 'danger')
                return redirect(url_for('resetpassword'))

            user = User.query.get(user_id)
            if user:
                # Hash the new password
                hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
                user.password = hashed_password
                db.session.commit()
                flash("Password reset successful. You can now log in.", 'success')
                return redirect(url_for('login'))

    return render_template('resetpassword.html', user=user, reset_password_mode=reset_password_mode, security_check_mode=security_check_mode)


# Main admin, job seeker and job recruiter dashboards to see the data
app.register_blueprint(dashboard)

app.register_blueprint(predictor)

@app.route('/logout')
def logout():
    session.clear()  # Clears all session data at once
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)

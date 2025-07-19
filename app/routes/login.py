from flask import Blueprint, redirect, render_template, url_for, request, flash, session
from app import user_collection, audit_log_collection, mail
from app.forms import LoginForm, ResetRequestForm, ResetPassword
import bcrypt
from datetime import datetime, timedelta
from bson import ObjectId
import logging
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from flask_mail import Message

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bp = Blueprint('login', __name__)

# Secret key for token generation (should be stored securely, e.g., in environment variables)
SECRET_KEY = 'your-secure-secret-key'  # Replace with a secure key
serializer = URLSafeTimedSerializer(SECRET_KEY)

@bp.route('/')
@bp.route('/login', methods=['GET'])
def login():
    form = LoginForm()
    role = session.get('role', 'normal')
    username = session.get('username')
    email = session.get('email')
    return render_template('login.html', form=form, role=role, username=username, email=email)

@bp.route('/login', methods=['POST'])
def login_post():
    form = LoginForm()
    if form.validate_on_submit():
        # Find user by email
        user = user_collection.find_one({'email': form.email.data})
        if user and bcrypt.checkpw(form.password.data.encode('utf-8'), user['password'].encode('utf-8')):
            # Store user info in session
            session['user_id'] = str(user['_id'])
            session['username'] = user['username']
            session['email'] = user['email']
            session['role'] = user['role']
            session.modified = True
            # Update user status and timestamps
            current_time = datetime.utcnow().isoformat() + 'Z'
            update_result = user_collection.update_one(
                {'_id': user['_id']},
                {
                    '$set': {
                        'status': True,
                        'last_visited': current_time,
                        'login_time': current_time
                    }
                }
            )
            if update_result.modified_count == 0:
                logger.warning(f"Failed to update user status for user_id: {user['_id']}, email: {user['email']}")
                flash('Warning: User status update failed.', 'warning')
            # Log login event
            try:
                audit_log_collection.insert_one({
                    'user_id': user['_id'],
                    'email': user['email'],
                    'event_type': 'login',
                    'timestamp': current_time,
                    'ip_address': request.remote_addr
                })
                logger.info(f"Logged login event for user_id: {user['_id']}, email: {user['email']}")
            except Exception as e:
                logger.error(f"Failed to log login event for user_id: {user['_id']}: {str(e)}")
                flash(f'Warning: Failed to log login event: {str(e)}', 'warning')
            flash(f'Login successful! Welcome {user["username"]}', 'success')
            return redirect(url_for('home.home'))
        else:
            flash('Invalid email or password.', 'danger')
            return redirect(url_for('login.login'))
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(error, 'danger')
        return redirect(url_for('login.login'))

@bp.route('/logout', methods=['GET'])
def logout():
    user_id = session.get('user_id')
    if user_id:
        try:
            user = user_collection.find_one({'_id': ObjectId(user_id)})
            if user and user.get('login_time'):
                login_time = datetime.fromisoformat(user['login_time'].replace('Z', '+00:00'))
                logout_time = datetime.utcnow()
                duration = (logout_time - login_time).total_seconds()
                # Update session_duration
                update_result = user_collection.update_one(
                    {'_id': ObjectId(user_id)},
                    {
                        '$set': {
                            'status': False,
                            'login_time': None
                        },
                        '$inc': {'session_duration': duration}
                    }
                )
                if update_result.modified_count == 0:
                    logger.warning(f"Failed to update logout status for user_id: {user_id}, email: {user.get('email', '')}")
                    flash('Warning: User logout update failed.', 'warning')
                # Log logout event
                audit_log_collection.insert_one({
                    'user_id': ObjectId(user_id),
                    'email': user.get('email', ''),
                    'event_type': 'logout',
                    'timestamp': logout_time.isoformat() + 'Z',
                    'ip_address': request.remote_addr
                })
                logger.info(f"Logged logout event for user_id: {user_id}, email: {user.get('email', '')}")
            else:
                logger.warning(f"Invalid user or login_time for user_id: {user_id}")
        except Exception as e:
            logger.error(f"Error during logout for user_id: {user_id}: {str(e)}")
            flash(f'Error during logout: {str(e)}', 'danger')
    session.clear()
    session.modified = True
    flash('You have been logged out.', 'success')
    return redirect(url_for('login.login'))

@bp.route('/reset_password', methods=['GET', 'POST'])
def reset_password_request():
    form = ResetRequestForm()
    logger.info(f"Reset password request received, method: {request.method}, email: {form.email.data if request.method == 'POST' else 'N/A'}")
    if request.method == 'POST':
        if form.validate_on_submit():
            logger.info("Form validated successfully")
            user = user_collection.find_one({'email': form.email.data})
            if user:
                logger.info(f"User found with email: {user['email']}")
                # Generate token
                token = serializer.dumps(user['email'], salt='reset-password-salt')
                # Send email with reset token
                try:
                    reset_url = url_for('login.reset_password_confirm', token=token, _external=True)
                    msg = Message('Password Reset Request', recipients=[user['email']])
                    msg.body = f'Click the link to reset your password: {reset_url}\nThis link will expire in 60 minutes.'
                    logger.info(f"Attempting to send email to: {user['email']}, URL: {reset_url}")
                    mail.send(msg)
                    logger.info(f"Email sent successfully to: {user['email']}")
                    flash('A password reset link has been sent to your email.', 'success')
                except Exception as e:
                    logger.error(f"Failed to send reset email for email: {user['email']}: {str(e)}")
                    flash(f'Failed to send reset email: {str(e)}', 'danger')
                return redirect(url_for('login.reset_password_request'))
            else:
                logger.info(f"No user found for email: {form.email.data}")
                flash('No account found with that email.', 'danger')
        else:
            logger.info(f"Form validation failed, errors: {form.errors}")
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f"Validation error in {field}: {error}", 'danger')
    else:
        logger.info("GET request received for reset password")
    return render_template('res_password.html', form=form, step='request')

@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password_confirm(token):
    form = ResetPassword()
    try:
        email = serializer.loads(token, salt='reset-password-salt', max_age=3600)  # 60 minutes = 3600 seconds
        if request.method == 'POST' and form.validate_on_submit():
            user = user_collection.find_one({'email': email})
            if user:
                hashed_password = bcrypt.hashpw(form.new_password.data.encode('utf-8'), bcrypt.gensalt())
                update_result = user_collection.update_one(
                    {'_id': user['_id']},
                    {'$set': {'password': hashed_password.decode('utf-8')}}
                )
                if update_result.modified_count > 0:
                    logger.info(f"Password reset successful for email: {email}")
                    flash('Your password has been reset successfully. Please log in.', 'success')
                    return redirect(url_for('login.login'))
                else:
                    logger.error(f"Failed to update password for email: {email}")
                    flash('Failed to reset password. Please try again.', 'danger')
            else:
                flash('Invalid user for this token.', 'danger')
    except SignatureExpired:
        flash('The reset link has expired. Please request a new one.', 'danger')
        return redirect(url_for('login.reset_password_request'))
    except BadSignature:
        flash('Invalid reset link. Please request a new one.', 'danger')
        return redirect(url_for('login.reset_password_request'))
    return render_template('res_password.html', form=form, step='confirm', token=token)
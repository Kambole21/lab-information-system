from flask import Flask, flash, session, request, url_for, redirect
from pymongo import MongoClient
from datetime import timedelta, datetime
from bson import ObjectId
import logging
from flask_mail import Mail, Message

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder="templates")
app.config['SECRET_KEY'] = "19a04e96a290e2fd739c829ba58c28c7"
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=120)  # Sessions expire after 120 minutes

# Email configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'kambole520@gmail.com'
app.config['MAIL_PASSWORD'] = 'rupi ebtg vjzw wpdk'  # Ensure no extra spaces
app.config['MAIL_DEFAULT_SENDER'] = 'kambole520@gmail.com'  # Explicitly set sender

mail = Mail(app)

# MongoDB setup
# MongoDB setup
Database = MongoClient('mongodb+srv://nyokasikazwe:QSACZ4fBHZrWK0vc@cluster0.qz5g7db.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
db = Database['zari_data']

# Collections
water_analysis_collection = db['Water Analysis Report']
water_worksheet_collection = db['Water Analysis Worksheet Form']
trace_worksheet_collection = db['Trace Work Sheet Form']
soil_analysis_form_collection = db['Soil Analysis Report Form']
ph_trace_form_collection = db['Ph, P, Bases, & Trace Analysis Form']
organic_carbon_nitrogent_collection = db['Organic, Carbon, Nitrogen']
equipment_collection = db['Equipment Operation Log Book']
user_collection = db['users']
audit_log_collection = db['audit_log']
pending_users_collection = db['pending_users']  # New collection for pending users
water_analysis_versions_collection = db['water_analysis_versions']

# Indexes for performance
audit_log_collection.create_index([('user_id', 1), ('timestamp', -1)])
pending_users_collection.create_index([('email', 1)])
pending_users_collection.create_index([('username', 1)])

# Create default ultra_superuser if not exists
import bcrypt
from datetime import datetime
default_email = 'kambole520@yahoo.com'
default_password = '12345678'
default_username = 'admin_kambole'
if not user_collection.find_one({'email': default_email}):
    hashed_password = bcrypt.hashpw(default_password.encode('utf-8'), bcrypt.gensalt())
    user_collection.insert_one({
        'email': default_email,
        'username': default_username,
        'password': hashed_password.decode('utf-8'),
        'role': 'ultra_superuser',
        'status': True,
        'first_name': 'Admin',
        'last_name': 'Kambole',
        'phone_number': 'N/A',
        'nationality': 'N/A',
        'profession': 'Administrator',
        'province': 'N/A',
        'district': 'N/A',
        'department': 'Administration',
        'session_duration': 0,
        'submission_time': datetime.utcnow().isoformat() + 'Z'
    })
    logger.info(f"Default ultra_superuser created: {default_email}")

# Define datetimeformat filter
@app.template_filter('datetimeformat')
def datetimeformat(value):
    if isinstance(value, datetime):
        return value.strftime('%Y-%m-%d')
    return value

@app.before_request
def check_session_timeout():
    # Skip for login, registration, reset password, and static files
    exempt_paths = [
        url_for('login.login'),
        url_for('registration.register'),
        url_for('login.reset_password_request'),
        url_for('login.reset_password_confirm', token='dummy'),  # Using a dummy token for the dynamic route
    ]
    if request.path in exempt_paths or request.path.startswith('/static/'):
        return

    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login.login'))

    try:
        user = user_collection.find_one({'_id': ObjectId(user_id)})
        if not user:
            session.clear()
            return redirect(url_for('login.login'))

        # Check access level for certain blueprints
        requested_blueprint = request.blueprint
        if requested_blueprint in ['manage', 'request_bp']:
            if user.get('role') not in ['superuser', 'ultra_superuser']:
                flash('You do not have permission to access this page', 'danger')
                return redirect(url_for('home.home'))

        # Check session timeout
        if user and user.get('status') and user.get('login_time'):
            login_time = datetime.fromisoformat(user['login_time'].replace('Z', '+00:00'))
            current_time = datetime.utcnow().replace(tzinfo=login_time.tzinfo)
            session_duration = (current_time - login_time).total_seconds()

            if session_duration > app.config['PERMANENT_SESSION_LIFETIME'].total_seconds():
                logger.info(f"Session timeout for user_id: {user_id}, email: {user.get('email', '')}")

                # Update user status and increment session_duration
                update_result = user_collection.update_one(
                    {'_id': ObjectId(user_id)},
                    {
                        '$set': {'status': False, 'login_time': None},
                        '$inc': {'session_duration': session_duration}
                    }
                )

                if update_result.modified_count == 0:
                    logger.warning(f"Failed to update user status for user_id: {user_id}")

                # Audit log
                audit_log_collection.insert_one({
                    'user_id': ObjectId(user_id),
                    'email': user.get('email', ''),
                    'event_type': 'session_timeout',
                    'timestamp': current_time.isoformat() + 'Z',
                    'ip_address': request.remote_addr
                })

                session.clear()
                return redirect(url_for('login.login'))

    except Exception as e:
        logger.error(f"Error in session timeout check for user_id: {user_id}: {str(e)}")
        session.clear()
        return redirect(url_for('login.login'))

# Test email function
@app.route('/test-email')
def test_email():
    try:
        msg = Message('Test Email', recipients=['kambole520@gmail.com'])
        msg.body = 'This is a test email sent from Flask.'
        mail.send(msg)
        logger.info('Test email sent successfully.')
        flash('Test email sent successfully.', 'success')
    except Exception as e:
        logger.error(f'Failed to send test email: {str(e)}')
        flash(f'Failed to send test email: {str(e)}', 'danger')
    return redirect(url_for('login.login'))

# Import and register blueprints
from app.routes import (
    home, water_analysis, equipment, soil, trace, water_worksheet,
    ocn, ph_trace_form, lab_equip, submit, manager, profile,
    registration, login, field_trail, my_files
)

app.register_blueprint(home.bp)
app.register_blueprint(water_analysis.bp)
app.register_blueprint(equipment.bp)
app.register_blueprint(soil.bp)
app.register_blueprint(trace.bp)
app.register_blueprint(water_worksheet.bp)
app.register_blueprint(ocn.bp)
app.register_blueprint(ph_trace_form.bp)
app.register_blueprint(lab_equip.bp)
app.register_blueprint(submit.bp)
app.register_blueprint(manager.bp)
app.register_blueprint(profile.bp)
app.register_blueprint(registration.bp)
app.register_blueprint(login.bp)
app.register_blueprint(field_trail.bp)
app.register_blueprint(my_files.bp)
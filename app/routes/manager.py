from flask import Blueprint, render_template, jsonify, make_response, session, request, redirect, url_for
from app import user_collection, pending_users_collection, audit_log_collection
from datetime import datetime
from bson import ObjectId
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bp = Blueprint('manage', __name__)

@bp.route('/user_management')
def manage():
    # Check user role
    if session.get('role') not in ['superuser', 'ultra_superuser']:
        return redirect(url_for('home.home'))
    
    # Fetch all users from user_collection
    users = list(user_collection.find())
    # Format user data for template
    for user in users:
        user['id'] = str(user['_id'])  # Convert ObjectId to string
        user['full_name'] = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
        user['roles'] = [user.get('role', 'normal').capitalize()]
        if user.get('last_visited'):
            try:
                user['last_visited'] = datetime.strptime(user['last_visited'], '%Y-%m-%dT%H:%M:%S.%fZ').strftime('%B %d, %Y %H:%M:%S')
            except ValueError:
                user['last_visited'] = 'Invalid date'
        else:
            user['last_visited'] = 'Never'
        # Format session_duration (in minutes)
        session_duration = user.get('session_duration', 0)
        user['session_duration'] = f"{session_duration / 60:.2f} minutes" if session_duration else "0 minutes"
    
    # Fetch pending users
    pending_users = list(pending_users_collection.find())
    for pending_user in pending_users:
        pending_user['id'] = str(pending_user['_id'])
        pending_user['full_name'] = f"{pending_user.get('first_name', '')} {pending_user.get('last_name', '')}".strip()
        submission_time = pending_user.get('submission_time')
        if submission_time:
            try:
                pending_user['submission_time'] = datetime.strptime(submission_time, '%Y-%m-%dT%H:%M:%S.%fZ').strftime('%B %d, %Y %H:%M:%S')
            except ValueError:
                pending_user['submission_time'] = 'Invalid date'
        else:
            pending_user['submission_time'] = 'Not available'
    
    # Only show sensitive information to ultra_superusers
    show_sensitive = session.get('role') == 'ultra_superuser'
    
    response = make_response(render_template('manage.html', users=users, pending_users=pending_users, show_sensitive=show_sensitive))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return response

@bp.route('/user/<id>')
def get_user(id):
    # Check user role
    if session.get('role') not in ['superuser', 'ultra_superuser']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        user = user_collection.find_one({'_id': ObjectId(id)})
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Prepare user data for JSON response
        session_duration = user.get('session_duration', 0)
        user_data = {
            'id': str(user['_id']),
            'full_name': f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
            'username': user.get('username', ''),
            'first_name': user.get('first_name', ''),
            'last_name': user.get('last_name', ''),
            'email': user.get('email', ''),
            'phone_number': user.get('phone_number', ''),
            'nationality': user.get('nationality', ''),
            'profession': user.get('profession', ''),
            'status': 'Active' if user.get('status', False) else 'Not active',
            'last_visited': datetime.strptime(user['last_visited'], '%Y-%m-%dT%H:%M:%S.%fZ').strftime('%B %d, %Y %H:%M:%S') if user.get('last_visited') else 'Never',
            'roles': [user.get('role', 'normal').capitalize()],
            'session_duration': f"{session_duration / 60:.2f} minutes" if session_duration else "0 minutes"
        }
        
        # Only include sensitive information for ultra_superusers
        if session.get('role') != 'ultra_superuser':
            sensitive_fields = ['phone_number', 'nationality', 'profession']
            for field in sensitive_fields:
                if field in user_data:
                    user_data[field] = '*****'
        
        response = make_response(jsonify(user_data))
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        return response
    except Exception as e:
        logger.error(f"Error fetching user {id}: {str(e)}")
        return jsonify({'error': str(e)}), 400

@bp.route('/user/<id>', methods=['PUT'])
def update_user(id):
    if session.get('role') != 'ultra_superuser':
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        update_data = {
            'first_name': data.get('first_name'),
            'last_name': data.get('last_name'),
            'phone_number': data.get('phone_number'),
            'nationality': data.get('nationality'),
            'profession': data.get('profession'),
            'status': data.get('status'),
            'role': data.get('role')
        }
        
        # Remove None values
        update_data = {k: v for k, v in update_data.items() if v is not None}
        
        result = user_collection.update_one(
            {'_id': ObjectId(id)},
            {'$set': update_data}
        )
        
        if result.modified_count == 0:
            return jsonify({'error': 'No changes made'}), 400
        
        # Log the update
        audit_log_collection.insert_one({
            'user_id': ObjectId(session.get('user_id')),
            'target_user_id': ObjectId(id),
            'event_type': 'user_update',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'ip_address': request.remote_addr,
            'changes': update_data
        })
        
        return jsonify({'message': 'User updated successfully'})
    except Exception as e:
        logger.error(f"Error updating user {id}: {str(e)}")
        return jsonify({'error': str(e)}), 400

@bp.route('/pending_user/<id>', methods=['GET'])
def get_pending_user(id):
    if session.get('role') not in ['superuser', 'ultra_superuser']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        pending_user = pending_users_collection.find_one({'_id': ObjectId(id)})
        if not pending_user:
            return jsonify({'error': 'Pending user not found'}), 404
        
        user_data = {
            'id': str(pending_user['_id']),
            'full_name': f"{pending_user.get('first_name', '')} {pending_user.get('last_name', '')}".strip(),
            'username': pending_user.get('username', ''),
            'first_name': pending_user.get('first_name', ''),
            'last_name': pending_user.get('last_name', ''),
            'email': pending_user.get('email', ''),
            'phone_number': pending_user.get('phone_number', ''),
            'nationality': pending_user.get('nationality', ''),
            'profession': pending_user.get('profession', ''),
            'role': pending_user.get('role', 'normal').capitalize(),
            'province': pending_user.get('province', ''),
            'district': pending_user.get('district', ''),
            'department': pending_user.get('department', ''),
            'status': pending_user.get('status', 'pending'),
            'submission_time': datetime.strptime(pending_user['submission_time'], '%Y-%m-%dT%H:%M:%S.%fZ').strftime('%B %d, %Y %H:%M:%S') if pending_user.get('submission_time') else 'Not available'
        }
        
        # Only include sensitive information for ultra_superusers
        if session.get('role') != 'ultra_superuser':
            sensitive_fields = ['phone_number', 'nationality', 'profession']
            for field in sensitive_fields:
                if field in user_data:
                    user_data[field] = '*****'
        
        response = make_response(jsonify(user_data))
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        return response
    except Exception as e:
        logger.error(f"Error fetching pending user {id}: {str(e)}")
        return jsonify({'error': str(e)}), 400

@bp.route('/pending_user/<id>/approve', methods=['POST'])
def approve_pending_user(id):
    if session.get('role') not in ['superuser', 'ultra_superuser']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        pending_user = pending_users_collection.find_one({'_id': ObjectId(id)})
        if not pending_user:
            return jsonify({'error': 'Pending user not found'}), 404
        
        # Prepare user data for user_collection
        user_data = {
            'email': pending_user['email'],
            'username': pending_user['username'],
            'first_name': pending_user['first_name'],
            'last_name': pending_user['last_name'],
            'phone_number': pending_user['phone_number'],
            'nationality': pending_user['nationality'],
            'profession': pending_user['profession'],
            'role': pending_user['role'],
            'province': pending_user['province'],
            'district': pending_user['district'],
            'department': pending_user['department'],
            'password': pending_user['password'],
            'status': False,  # New users start inactive
            'session_duration': 0,
            'last_visited': None,
            'login_time': None
        }
        
        # Insert into user_collection
        user_collection.insert_one(user_data)
        
        # Remove from pending_users_collection
        pending_users_collection.delete_one({'_id': ObjectId(id)})
        
        # Log the approval
        audit_log_collection.insert_one({
            'user_id': ObjectId(session.get('user_id')),
            'target_user_id': ObjectId(id),
            'event_type': 'user_approved',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'ip_address': request.remote_addr,
            'changes': {'email': pending_user['email'], 'username': pending_user['username']}
        })
        
        return jsonify({'message': 'User approved successfully'})
    except Exception as e:
        logger.error(f"Error approving pending user {id}: {str(e)}")
        return jsonify({'error': str(e)}), 400

@bp.route('/pending_user/<id>/reject', methods=['POST'])
def reject_pending_user(id):
    if session.get('role') not in ['superuser', 'ultra_superuser']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        pending_user = pending_users_collection.find_one({'_id': ObjectId(id)})
        if not pending_user:
            return jsonify({'error': 'Pending user not found'}), 404
        
        # Remove from pending_users_collection
        pending_users_collection.delete_one({'_id': ObjectId(id)})
        
        # Log the rejection
        audit_log_collection.insert_one({
            'user_id': ObjectId(session.get('user_id')),
            'target_user_id': ObjectId(id),
            'event_type': 'user_rejected',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'ip_address': request.remote_addr,
            'changes': {'email': pending_user['email'], 'username': pending_user['username']}
        })
        
        return jsonify({'message': 'User registration rejected'})
    except Exception as e:
        logger.error(f"Error rejecting pending user {id}: {str(e)}")
        return jsonify({'error': str(e)}), 400
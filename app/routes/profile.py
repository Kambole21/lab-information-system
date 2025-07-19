from flask import Blueprint, render_template, redirect, url_for, session, flash
from app import user_collection

bp = Blueprint('profile', __name__)

@bp.route('/profile', methods=['GET'])
def profile():
    role = session.get('role', 'normal')
    if 'email' not in session:
        flash('Please log in to view your profile.', 'danger')
        return redirect(url_for('login.login'))
    
    user = user_collection.find_one({'email': session['email']})
    if not user:
        flash('User not found. Please log in again.', 'danger')
        return redirect(url_for('login.login'))
    
    # Ensure profile_picture is included (defaults to None if not set)
    user['profile_picture'] = user.get('profile_picture', None)
    return render_template('profile.html', user=user, role = role)
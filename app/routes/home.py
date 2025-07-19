from flask import Blueprint, render_template, redirect, url_for, session, flash
from app import user_collection
from app.forms import LoginForm

bp = Blueprint('home', __name__)

@bp.route('/Home_Page')
def home():
    email = session.get('email')
    role = session.get('role', 'normal')
    username = session.get('username')
    user = None
    if email:
        user = user_collection.find_one({'email': email})
        if not user:
            flash('User not found. Please log in again.', 'danger')
            return redirect(url_for('login.login'))
    
    return render_template('home.html', username=username, role=role, email=email, user=user)
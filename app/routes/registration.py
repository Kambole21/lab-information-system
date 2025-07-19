from flask import Blueprint, redirect, render_template, url_for, request, flash
from app import user_collection, pending_users_collection
from app.forms import RegistrationForm
import bcrypt
from datetime import datetime

bp = Blueprint('registration', __name__)

@bp.route('/registration_page', methods=['GET'])
def register():
    form = RegistrationForm()
    return render_template('registration.html', form=form)

@bp.route('/registration_page', methods=['POST'])
def register_post():
    form = RegistrationForm()
    
    # Check if this is a partial submission for province change
    if request.form.get('province') and not form.validate_on_submit():
        # Populate form with submitted data to preserve user input
        form = RegistrationForm(request.form)
        selected_province = request.form.get('province')
        if selected_province:
            form.province.data = selected_province
            # Update district choices based on selected province
            form.district.choices = [(d, d) for d in form.district_map.get(selected_province, [])] or [('', 'Select a district')]
        return render_template('registration.html', form=form)

    # Handle full form submission
    if form.validate_on_submit():
        # Check if email or username already exists in user_collection or pending_users_collection
        existing_email = user_collection.find_one({'email': form.email.data})
        existing_username = user_collection.find_one({'username': form.username.data})
        pending_email = pending_users_collection.find_one({'email': form.email.data})
        pending_username = pending_users_collection.find_one({'username': form.username.data})
        if existing_email or pending_email:
            flash('Email already exists or is pending approval. Please use a different email.', 'danger')
            return redirect(url_for('registration.register'))
        if existing_username or pending_username:
            flash('Username already exists or is pending approval. Please choose a different username.', 'danger')
            return redirect(url_for('registration.register'))

        # Hash the password
        hashed_password = bcrypt.hashpw(form.password.data.encode('utf-8'), bcrypt.gensalt())

        # Prepare pending user data
        pending_user_data = {
            'email': form.email.data,
            'username': form.username.data,
            'first_name': form.fname.data,
            'last_name': form.lnname.data,
            'phone_number': form.phone_number.data,
            'nationality': form.nationality.data,
            'profession': form.profession.data,
            'role': form.role.data,
            'province': form.province.data,
            'district': form.district.data,
            'department': form.department.data,
            'password': hashed_password.decode('utf-8'),
            'status': 'pending',
            'submission_time': datetime.utcnow().isoformat() + 'Z'
        }

        # Insert into pending_users_collection
        pending_users_collection.insert_one(pending_user_data)
        flash('Registration submitted for approval. You will be notified once approved.', 'success')
        return redirect(url_for('login.login'))
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(error, 'danger')
        return render_template('registration.html', form=form)
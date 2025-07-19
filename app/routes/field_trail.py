from flask import Blueprint, render_template, flash, request, redirect, url_for, session, Flask
bp = Blueprint('field_trails', __name__)
@bp.route('/Field_Trials')
def field_trails():
	role = session.get('role', 'normal')
	return render_template('field_trail.html', role = role)
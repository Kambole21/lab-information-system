from flask import Blueprint, render_template, flash, request, redirect, url_for, session, Flask

bp = Blueprint('res_password', __name__)
@bp.route('/Rest_Password')
def rest():
	return render_template('res_password.html')
from flask import Flask, Blueprint, redirect, render_template, url_for, request, flash, session

bp = Blueprint('lab_equip', __name__)
@bp.route('/lab_equip')
def lab_equip():
	role = session.get('role', 'normal')
	return render_template("lab_equip.html", role = role)
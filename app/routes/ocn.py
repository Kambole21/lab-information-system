from flask import Blueprint, render_template, flash, request, redirect, url_for, session
from app import organic_carbon_nitrogent_collection
from bson import ObjectId
from datetime import datetime

bp = Blueprint('organic_carbon_nitrogen', __name__)

@bp.route('/organic_carbon_nitrogen', methods=['GET', 'POST'])
def organic_carbon_nitrogen():
    if request.method == 'POST':
        try:
            # Collect form data
            form_data = {
                'date': request.form.get('date'),
                'lab_number': request.form.get('lab_number'),
                'left_table': [
                    {
                        'serial_number': i,
                        'lab_no': request.form.get(f'left_lab_no{i}', ''),
                        'ini_vol': float(request.form.get(f'left_ini_vol{i}', 0)) if request.form.get(f'left_ini_vol{i}') else None,
                        'titre_vol': float(request.form.get(f'left_titre_vol{i}', 0)) if request.form.get(f'left_titre_vol{i}') else None,
                        'final_vol': float(request.form.get(f'left_final_vol{i}', 0)) if request.form.get(f'left_final_vol{i}') else None
                    } for i in range(1, 31)
                ],
                'right_table': [
                    {
                        'serial_number': i,
                        'lab_no': request.form.get(f'right_lab_no{i}', ''),
                        'ini_vol': float(request.form.get(f'right_ini_vol{i}', 0)) if request.form.get(f'right_ini_vol{i}') else None,
                        'titre_vol': float(request.form.get(f'right_titre_vol{i}', 0)) if request.form.get(f'right_titre_vol{i}') else None,
                        'final_vol': float(request.form.get(f'right_final_vol{i}', 0)) if request.form.get(f'right_final_vol{i}') else None
                    } for i in range(1, 31)
                ],
                'analyzed_by': {
                    'name': request.form.get('analyzed_by'),
                    'date': request.form.get('date_analyzed')
                },
                'checked_by': {
                    'name': request.form.get('checked_by'),
                    'date': request.form.get('date_checked')
                },
                'created_at': datetime.utcnow(),
                'created_by': session.get('username', 'Unknown'),
                'comment': request.form.get('comment')
            }

            # Basic validation
            if not form_data['date'] or not form_data['lab_number']:
                flash('Please fill in all required metadata fields: Date and Lab #.', 'danger')
                return redirect(url_for('organic_carbon_nitrogen.organic_carbon_nitrogen'))

            if not form_data['analyzed_by']['name'] or not form_data['checked_by']['name']:
                flash('Please provide Analyzed By and Checked By names.', 'danger')
                return redirect(url_for('organic_carbon_nitrogen.organic_carbon_nitrogen'))

            # Ensure at least one row in either table has data
            has_row_data = False
            for table in ['left_table', 'right_table']:
                for row in form_data[table]:
                    if row['lab_no'] or any(
                        value is not None for key, value in row.items() if key in ['ini_vol', 'titre_vol', 'final_vol']
                    ):
                        has_row_data = True
                        break
                if has_row_data:
                    break
            if not has_row_data:
                flash('Please provide data for at least one row in either table.', 'danger')
                return redirect(url_for('organic_carbon_nitrogen.organic_carbon_nitrogen'))

            # Check if updating an existing document
            if 'id' in request.form:
                try:
                    worksheet_id = ObjectId(request.form['id'])
                    form_data['edited_at'] = datetime.utcnow()
                    result = organic_carbon_nitrogent_collection.update_one(
                        {'_id': worksheet_id},
                        {'$set': form_data}
                    )
                    if result.modified_count:
                        flash('Organic Carbon & Nitrogen Worksheet updated successfully!', 'success')
                    else:
                        flash('No changes made to the worksheet.', 'warning')
                except Exception as e:
                    flash(f'Error updating worksheet: {str(e)}', 'danger')
            else:
                # Insert new document
                result = organic_carbon_nitrogent_collection.insert_one(form_data)
                if result.inserted_id:
                    flash('Organic Carbon & Nitrogen Worksheet submitted successfully!', 'success')
                else:
                    flash('Failed to submit the worksheet. Please try again.', 'danger')

            return redirect(url_for('submit.submit'))

        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'danger')
            return redirect(url_for('organic_carbon_nitrogen.organic_carbon_nitrogen'))

    # Handle GET request for creating or editing
    worksheet = {}
    if 'id' in request.args:
        try:
            worksheet = organic_carbon_nitrogent_collection.find_one({'_id': ObjectId(request.args['id'])})
            if not worksheet:
                flash('Organic Carbon & Nitrogen Worksheet not found.', 'danger')
                return redirect(url_for('submit.submit'))
        except Exception as e:
            flash(f'Error fetching worksheet: {str(e)}', 'danger')
            return redirect(url_for('submit.submit'))

    return render_template('organic_carbon_nitrogen.html', worksheet=worksheet)

@bp.route('/view_ocn/<id>')
def view_ocn(id):
    role = session.get('role', 'normal')
    try:
        worksheet = organic_carbon_nitrogent_collection.find_one({'_id': ObjectId(id)})
        if not worksheet:
            flash('Organic Carbon & Nitrogen Worksheet not found.', 'danger')
            return redirect(url_for('submit.submit'))
        return render_template('view_ocn.html', worksheet=worksheet, role = role)
    except Exception as e:
        flash(f'Error fetching worksheet: {str(e)}', 'danger')
        return redirect(url_for('submit.submit'))
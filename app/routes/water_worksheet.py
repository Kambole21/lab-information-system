from flask import Blueprint, render_template, flash, request, redirect, url_for, session
from app import water_worksheet_collection
from bson import ObjectId
from datetime import datetime

bp = Blueprint('water_worksheet', __name__)

@bp.route('/water_worksheet', methods=['GET', 'POST'])
def water_worksheet():
    if request.method == 'POST':
        try:
            # Collect form data
            form_data = {
                'samples': [
                    {
                        'sample_number': i,
                        'lab_no': request.form.get(f'labno{i}'),
                        'ph': float(request.form.get(f'ph_sample{i}', 0)) if request.form.get(f'ph_sample{i}') else None,
                        'ec': float(request.form.get(f'ec_sample{i}', 0)) if request.form.get(f'ec_sample{i}') else None,
                        'tds': float(request.form.get(f'tds_sample{i}', 0)) if request.form.get(f'tds_sample{i}') else None,
                        'resistivity': float(request.form.get(f'resistivity_sample{i}', 0)) if request.form.get(f'resistivity_sample{i}') else None,
                        'salinity': float(request.form.get(f'salinity_sample{i}', 0)) if request.form.get(f'salinity_sample{i}') else None,
                        'co3': float(request.form.get(f'co3_sample{i}', 0)) if request.form.get(f'co3_sample{i}') else None,
                        'hco3': float(request.form.get(f'hco3_sample{i}', 0)) if request.form.get(f'hco3_sample{i}') else None,
                        'cl': float(request.form.get(f'cl_sample{i}', 0)) if request.form.get(f'cl_sample{i}') else None,
                        'so4': float(request.form.get(f'so4_sample{i}', 0)) if request.form.get(f'so4_sample{i}') else None,
                        'k': float(request.form.get(f'k_sample{i}', 0)) if request.form.get(f'k_sample{i}') else None,
                        'ca': float(request.form.get(f'ca_sample{i}', 0)) if request.form.get(f'ca_sample{i}') else None,
                        'mg': float(request.form.get(f'mg_sample{i}', 0)) if request.form.get(f'mg_sample{i}') else None,
                        'na': float(request.form.get(f'na_sample{i}', 0)) if request.form.get(f'na_sample{i}') else None,
                        'cu': float(request.form.get(f'cu_sample{i}', 0)) if request.form.get(f'cu_sample{i}') else None,
                        'mn': float(request.form.get(f'mn_sample{i}', 0)) if request.form.get(f'mn_sample{i}') else None,
                        'fe': float(request.form.get(f'fe_sample{i}', 0)) if request.form.get(f'fe_sample{i}') else None,
                        'zn': float(request.form.get(f'zn_sample{i}', 0)) if request.form.get(f'zn_sample{i}') else None
                    } for i in range(1, 11)
                ],
                'date_checked': request.form.get('date_checked'),
                'analyzed_by': request.form.get('analyzed_by'),
                'checked_by': request.form.get('checked_by'),
                'created_at': datetime.utcnow(),
                'created_by': session.get('username', 'Unknown')
            }

            # Basic validation
            if not form_data['date_checked'] or not form_data['analyzed_by'] or not form_data['checked_by']:
                flash('Please fill in all required fields: Date, Analyzed By, and Checked By.', 'danger')
                return redirect(url_for('water_worksheet.water_worksheet'))

            # Ensure at least one sample has data
            has_sample_data = False
            for sample in form_data['samples']:
                if sample['lab_no'] or any(
                    value is not None for key, value in sample.items() if key not in ['sample_number', 'lab_no']
                ):
                    has_sample_data = True
                    break
            if not has_sample_data:
                flash('Please provide data for at least one sample.', 'danger')
                return redirect(url_for('water_worksheet.water_worksheet'))

            # Check if updating an existing document
            if 'id' in request.form:
                try:
                    worksheet_id = ObjectId(request.form['id'])
                    form_data['edited_at'] = datetime.utcnow()
                    result = water_worksheet_collection.update_one(
                        {'_id': worksheet_id},
                        {'$set': form_data}
                    )
                    if result.modified_count:
                        flash('Water analysis worksheet updated successfully!', 'success')
                    else:
                        flash('No changes made to the worksheet.', 'warning')
                except Exception as e:
                    flash(f'Error updating worksheet: {str(e)}', 'danger')
            else:
                # Insert new document
                result = water_worksheet_collection.insert_one(form_data)
                if result.inserted_id:
                    flash('Water analysis worksheet submitted successfully!', 'success')
                else:
                    flash('Failed to submit the worksheet. Please try again.', 'danger')

            return redirect(url_for('submit.submit'))

        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'danger')
            return redirect(url_for('water_worksheet.water_worksheet'))

    # Handle GET request for creating or editing
    worksheet = {}
    if 'id' in request.args:
        try:
            worksheet = water_worksheet_collection.find_one({'_id': ObjectId(request.args['id'])})
            if not worksheet:
                flash('Water Analysis Worksheet not found.', 'danger')
                return redirect(url_for('submit.submit'))
        except Exception as e:
            flash(f'Error fetching worksheet: {str(e)}', 'danger')
            return redirect(url_for('submit.submit'))

    return render_template('water_analysis_worksheet.html', worksheet=worksheet)

@bp.route('/view_water_worksheet/<id>')
def view_water_worksheet(id):
    role = session.get('role', 'normal')
    try:
        worksheet = water_worksheet_collection.find_one({'_id': ObjectId(id)})
        if not worksheet:
            flash('Water Analysis Worksheet not found.', 'danger')
            return redirect(url_for('submit.submit'))
        return render_template('view_water_worksheet.html', worksheet=worksheet, role = role)
    except Exception as e:
        flash(f'Error fetching worksheet: {str(e)}', 'danger')
        return redirect(url_for('submit.submit'))
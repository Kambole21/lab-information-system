from flask import Blueprint, redirect, render_template, url_for, request, flash, session
from app import ph_trace_form_collection
from bson import ObjectId
from datetime import datetime

bp = Blueprint('ph_bases', __name__)

@bp.route('/ph_bases', methods=['GET', 'POST'])
def ph_bases():
    worksheet = None
    if request.method == 'GET' and 'id' in request.args:
        try:
            worksheet_id = request.args.get('id')
            worksheet = ph_trace_form_collection.find_one({'_id': ObjectId(worksheet_id)})
            if not worksheet:
                flash('pH, Phosphorus, Bases & Traces Worksheet not found.', 'danger')
                return redirect(url_for('submit.submit'))
        except Exception as e:
            flash(f'Error fetching worksheet: {str(e)}', 'danger')
            return redirect(url_for('submit.submit'))

    if request.method == 'POST':
        try:
            # Collect form data
            form_data = {
                'lab_number': request.form.get('lab_number'),
                'date_of_analysis': request.form.get('date_of_analysis'),
                'calibration_table': [
                    {
                        'serial_number': i,
                        'p_std_conc': float(request.form.get(f'p_std_conc{i}', 0)) if request.form.get(f'p_std_conc{i}') else None,
                        'p_abs_reading': float(request.form.get(f'p_abs_reading{i}', 0)) if request.form.get(f'p_abs_reading{i}') else None,
                        'k_std_conc': float(request.form.get(f'k_std_conc{i}', 0)) if request.form.get(f'k_std_conc{i}') else None,
                        'k_abs_reading': float(request.form.get(f'k_abs_reading{i}', 0)) if request.form.get(f'k_abs_reading{i}') else None,
                        'ca_std_conc': float(request.form.get(f'ca_std_conc{i}', 0)) if request.form.get(f'ca_std_conc{i}') else None,
                        'ca_abs_reading': float(request.form.get(f'ca_abs_reading{i}', 0)) if request.form.get(f'ca_abs_reading{i}') else None,
                        'mg_std_conc': float(request.form.get(f'mg_std_conc{i}', 0)) if request.form.get(f'mg_std_conc{i}') else None,
                        'mg_abs_reading': float(request.form.get(f'mg_abs_reading{i}', 0)) if request.form.get(f'mg_abs_reading{i}') else None,
                        'na_std_conc': float(request.form.get(f'na_std_conc{i}', 0)) if request.form.get(f'na_std_conc{i}') else None,
                        'na_abs_reading': float(request.form.get(f'na_abs_reading{i}', 0)) if request.form.get(f'na_abs_reading{i}') else None
                    } for i in range(1, 6)
                ],
                'analysis_table': [
                    {
                        'serial_number': i,
                        'lab_no': request.form.get(f'lab_no{i}'),
                        'ph_cacl2': float(request.form.get(f'ph_cacl2{i}', 0)) if request.form.get(f'ph_cacl2{i}') else None,
                        'p_instrument_reading': float(request.form.get(f'p_instrument_reading{i}', 0)) if request.form.get(f'p_instrument_reading{i}') else None,
                        'p_df': float(request.form.get(f'p_df{i}', 0)) if request.form.get(f'p_df{i}') else None,
                        'p_mgl': float(request.form.get(f'p_mgl{i}', 0)) if request.form.get(f'p_mgl{i}') else None,
                        'k_instrument_reading': float(request.form.get(f'k_instrument_reading{i}', 0)) if request.form.get(f'k_instrument_reading{i}') else None,
                        'k_df': float(request.form.get(f'k_df{i}', 0)) if request.form.get(f'k_df{i}') else None,
                        'k_mgl': float(request.form.get(f'k_mgl{i}', 0)) if request.form.get(f'k_mgl{i}') else None,
                        'ca_instrument_reading': float(request.form.get(f'ca_instrument_reading{i}', 0)) if request.form.get(f'ca_instrument_reading{i}') else None,
                        'ca_df': float(request.form.get(f'ca_df{i}', 0)) if request.form.get(f'ca_df{i}') else None,
                        'ca_mgl': float(request.form.get(f'ca_mgl{i}', 0)) if request.form.get(f'ca_mgl{i}') else None,
                        'mg_instrument_reading': float(request.form.get(f'mg_instrument_reading{i}', 0)) if request.form.get(f'mg_instrument_reading{i}') else None,
                        'mg_df': float(request.form.get(f'mg_df{i}', 0)) if request.form.get(f'mg_df{i}') else None,
                        'mg_mgl': float(request.form.get(f'mg_mgl{i}', 0)) if request.form.get(f'mg_mgl{i}') else None,
                        'na_instrument_reading': float(request.form.get(f'na_instrument_reading{i}', 0)) if request.form.get(f'na_instrument_reading{i}') else None,
                        'na_df': float(request.form.get(f'na_df{i}', 0)) if request.form.get(f'na_df{i}') else None,
                        'na_mgl': float(request.form.get(f'na_mgl{i}', 0)) if request.form.get(f'na_mgl{i}') else None
                    } for i in range(1, 31)
                ],
                'analyzed_by': {
                    'name': request.form.get('analyzed_by'),
                    'date': request.form.get('date_checked')
                },
                'checked_by': {
                    'name': request.form.get('checked_by'),
                    'date': request.form.get('date_checked')
                },
                'created_at': datetime.utcnow(),
                'created_by': session.get('username', 'Unknown')
            }

            # Basic validation
            if not all([form_data['lab_number'], form_data['date_of_analysis'], form_data['analyzed_by']['name'], form_data['checked_by']['name'], form_data['checked_by']['date']]):
                flash('Please fill in all required fields: Lab #, Date of Analysis, Analyzed By, Checked By, and Date Checked.', 'danger')
                return redirect(url_for('ph_bases.ph_bases'))

            # Ensure at least one row in the analysis table has data
            has_analysis_data = False
            for row in form_data['analysis_table']:
                if row['lab_no'] or any(
                    value is not None for key, value in row.items() if key in [
                        'ph_cacl2', 'p_instrument_reading', 'p_df', 'p_mgl', 'k_instrument_reading', 'k_df', 'k_mgl',
                        'ca_instrument_reading', 'ca_df', 'ca_mgl', 'mg_instrument_reading', 'mg_df', 'mg_mgl',
                        'na_instrument_reading', 'na_df', 'na_mgl'
                    ]
                ):
                    has_analysis_data = True
                    break
            if not has_analysis_data:
                flash('Please provide data for at least one row in the analysis table.', 'danger')
                return redirect(url_for('ph_bases.ph_bases'))

            # Insert or update in MongoDB
            if worksheet:
                form_data['edited_at'] = datetime.utcnow()
                result = ph_trace_form_collection.update_one(
                    {'_id': ObjectId(worksheet['_id'])},
                    {'$set': form_data}
                )
                if result.modified_count:
                    flash('pH, Phosphorus, Bases & Traces Worksheet updated successfully!', 'success')
                else:
                    flash('No changes made to the worksheet.', 'warning')
            else:
                result = ph_trace_form_collection.insert_one(form_data)
                if result.inserted_id:
                    flash('pH, Phosphorus, Bases & Traces Worksheet submitted successfully!', 'success')
                else:
                    flash('Failed to submit the worksheet. Please try again.', 'danger')
            return redirect(url_for('submit.submit'))

        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'danger')
            return redirect(url_for('ph_bases.ph_bases'))

    return render_template('ph_bases.html', worksheet=worksheet or {})

@bp.route('/view_ph/<id>')
def view_ph(id):
    role = session.get('role', 'normal')
    try:
        worksheet = ph_trace_form_collection.find_one({'_id': ObjectId(id)})
        if not worksheet:
            flash('pH, Phosphorus, Bases & Traces Worksheet not found.', 'danger')
            return redirect(url_for('submit.submit'))
        return render_template('view_ph.html', worksheet=worksheet, role = role)
    except Exception as e:
        flash(f'Error fetching worksheet: {str(e)}', 'danger')
        return redirect(url_for('submit.submit'))
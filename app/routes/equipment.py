from flask import Flask, Blueprint, redirect, render_template, url_for, request, flash, jsonify, Response, session
from app import equipment_collection
from datetime import datetime
from bson import ObjectId
import csv
from io import StringIO

bp = Blueprint('equipment', __name__)

@bp.route('/equipment', methods=['GET', 'POST'])
def equipment():
    if request.method == 'POST':
        try:
            # Collect equipment details
            equipment_data = {
                'equipment_name': request.form.get('equipmentname'),
                'location': request.form.get('locationname'),
                'model_no': request.form.get('modelno'),
                'serial_no': request.form.get('serialno'),
                'manufacturer': request.form.get('manufacturername'),
                'log_entries': [],
                'created_at': datetime.utcnow(),
                'created_by': session.get('username', 'Unknown')  # Add created_by field
            }

            # Basic validation for equipment details
            if not equipment_data['equipment_name'] or not equipment_data['location']:
                flash('Please fill in the Equipment Name and Location fields.', 'danger')
                return redirect(url_for('equipment.equipment'))

            # Collect log entries (dynamic rows)
            row_count = 1
            while f'date{row_count}' in request.form:
                log_entry = {
                    'serial_number': row_count,
                    'date': request.form.get(f'date{row_count}'),
                    'operator': request.form.get(f'operator{row_count}'),
                    'analysis_done': request.form.get(f'analysis{row_count}'),
                    'no_of_samples': int(request.form.get(f'samples{row_count}', 0)) if request.form.get(f'samples{row_count}') else None,
                    'instrument_performance': request.form.get(f'performance{row_count}')
                }

                # Validate log entry
                if not log_entry['date'] or not log_entry['operator'] or not log_entry['analysis_done']:
                    flash(f'Please fill in all required fields for log entry {row_count}.', 'danger')
                    return redirect(url_for('equipment.equipment'))

                equipment_data['log_entries'].append(log_entry)
                row_count += 1

            # Ensure at least one log entry
            if not equipment_data['log_entries']:
                flash('Please add at least one log entry.', 'danger')
                return redirect(url_for('equipment.equipment'))

            # Handle edit case
            if 'id' in request.form:
                equipment_data['edited_at'] = datetime.utcnow()  # Add edited_at timestamp
                equipment_collection.update_one(
                    {'_id': ObjectId(request.form['id'])},
                    {'$set': equipment_data}
                )
                flash('Equipment operation log updated successfully!', 'success')
            else:
                # Insert into MongoDB
                result = equipment_collection.insert_one(equipment_data)
                if result.inserted_id:
                    flash('Equipment operation log submitted successfully!', 'success')
                else:
                    flash('Failed to submit the log. Please try again.', 'danger')

            return redirect(url_for('submit.submit'))

        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'danger')
            return redirect(url_for('equipment.equipment'))

    # Handle GET request for editing
    worksheet = {}
    if 'id' in request.args:
        try:
            worksheet = equipment_collection.find_one({'_id': ObjectId(request.args['id'])})
            if not worksheet:
                flash('Equipment log not found.', 'danger')
                return redirect(url_for('submit.submit'))
        except Exception as e:
            flash(f'Error fetching equipment log: {str(e)}', 'danger')
            return redirect(url_for('submit.submit'))

    return render_template('equipment_log.html', worksheet=worksheet)

@bp.route('/view_equipment_log/<id>')
def view_equipment_log(id):
    role = session.get('role', 'normal')
    try:
        worksheet = equipment_collection.find_one({'_id': ObjectId(id)})
        if not worksheet:
            flash('Equipment log not found.', 'danger')
            return redirect(url_for('submit.submit'))
        return render_template('view_equipment_log.html', worksheet=worksheet, role = role)
    except Exception as e:
        flash(f'Error fetching equipment log: {str(e)}', 'danger')
        return redirect(url_for('submit.submit'))

@bp.route('/download_csv/<id>')
def download_csv(id):
    try:
        worksheet = equipment_collection.find_one({'_id': ObjectId(id)})
        if not worksheet:
            flash('Equipment log not found.', 'danger')
            return redirect(url_for('submit.submit'))

        output = StringIO()
        writer = csv.writer(output)
        
        # Write equipment details
        writer.writerow(['Equipment Name', worksheet.get('equipment_name', '')])
        writer.writerow(['Location', worksheet.get('location', '')])
        writer.writerow(['Model No', worksheet.get('model_no', '')])
        writer.writerow(['Serial No', worksheet.get('serial_no', '')])
        writer.writerow(['Manufacturer', worksheet.get('manufacturer', '')])
        writer.writerow([])  # Empty row for separation
        
        # Write log entries
        writer.writerow(['S/N', 'Date', 'Operator', 'Analysis Done', 'No. of Samples', 'Instrument Performance'])
        for entry in worksheet.get('log_entries', []):
            writer.writerow([
                entry.get('serial_number', ''),
                entry.get('date', ''),
                entry.get('operator', ''),
                entry.get('analysis_done', ''),
                entry.get('no_of_samples', ''),
                entry.get('instrument_performance', '')
            ])

        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment;filename=equipment_log_{id}.csv'}
        )
    except Exception as e:
        flash(f'Error generating CSV: {str(e)}', 'danger')
        return redirect(url_for('submit.submit'))
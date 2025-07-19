from flask import Flask, Blueprint, redirect, render_template, url_for, request, flash, session
from app import soil_analysis_form_collection
from datetime import datetime
from bson.objectid import ObjectId

bp = Blueprint('soil', __name__)

@bp.route('/soil', methods=['GET', 'POST'])
def soil():
    role = session.get('role', 'normal')
    if request.method == 'POST':
        try:
            # Collect form data
            username = session.get('username')
            if not username:
                flash('Please log in to submit a soil analysis report.', 'danger')
                return redirect(url_for('login.login'))

            form_data = {
                'title': 'Soil Analysis Report Form',
                'lab_number': request.form.get('labNumber'),
                'farm_location': request.form.get('farmLocation'),
                'date_received': request.form.get('dateReceived'),
                'date_reported': request.form.get('dateReported'),
                'samples': [
                    {
                        'field': request.form.get(f'field{i}'),
                        'sample_ref': request.form.get(f'sampleRef{i}'),
                        'soil_depth': float(request.form.get(f'soilDepth{i}', 0)) if request.form.get(f'soilDepth{i}') else None,
                        'lab_no': request.form.get(f'labNo{i}'),
                        'texture': {
                            'value': request.form.get(f'textureValue{i}'),
                            'class': request.form.get(f'textureClass{i}')
                        },
                        'ph': {
                            'value': float(request.form.get(f'phValue{i}', 0)) if request.form.get(f'phValue{i}') else None,
                            'class': request.form.get(f'phClass{i}')
                        },
                        'conductivity': {
                            'value': float(request.form.get(f'conductivityValue{i}', 0)) if request.form.get(f'conductivityValue{i}') else None,
                            'class': request.form.get(f'conductivityClass{i}')
                        },
                        'org_carbon': {
                            'value': float(request.form.get(f'orgCarbonValue{i}', 0)) if request.form.get(f'orgCarbonValue{i}') else None,
                            'class': request.form.get(f'orgCarbonClass{i}')
                        },
                        'nitrogen': {
                            'value': float(request.form.get(f'nitrogenValue{i}', 0)) if request.form.get(f'nitrogenValue{i}') else None,
                            'class': request.form.get(f'nitrogenClass{i}')
                        },
                        'phosphorus_bray': {
                            'value': float(request.form.get(f'phosphorusBrayValue{i}', 0)) if request.form.get(f'phosphorusBrayValue{i}') else None,
                            'class': request.form.get(f'phosphorusBrayClass{i}')
                        },
                        'phosphorus_olsen': {
                            'value': request.form.get(f'phosphorusOlsenValue{i}'),
                            'class': request.form.get(f'phosphorusOlsenClass{i}')
                        },
                        'potassium': {
                            'value': float(request.form.get(f'potassiumValue{i}', 0)) if request.form.get(f'potassiumValue{i}') else None,
                            'class': request.form.get(f'potassiumClass{i}')
                        },
                        'calcium': {
                            'value': float(request.form.get(f'calciumValue{i}', 0)) if request.form.get(f'calciumValue{i}') else None,
                            'class': request.form.get(f'calciumClass{i}')
                        },
                        'magnesium': {
                            'value': float(request.form.get(f'magnesiumValue{i}', 0)) if request.form.get(f'magnesiumValue{i}') else None,
                            'class': request.form.get(f'magnesiumClass{i}')
                        },
                        'copper': {
                            'value': float(request.form.get(f'copperValue{i}', 0)) if request.form.get(f'copperValue{i}') else None,
                            'class': request.form.get(f'copperClass{i}')
                        },
                        'manganese': {
                            'value': float(request.form.get(f'manganeseValue{i}', 0)) if request.form.get(f'manganeseValue{i}') else None,
                            'class': request.form.get(f'manganeseClass{i}')
                        },
                        'iron': {
                            'value': float(request.form.get(f'ironValue{i}', 0)) if request.form.get(f'ironValue{i}') else None,
                            'class': request.form.get(f'ironClass{i}')
                        },
                        'zinc': {
                            'value': float(request.form.get(f'zincValue{i}', 0)) if request.form.get(f'zincValue{i}') else None,
                            'class': request.form.get(f'zincClass{i}')
                        }
                    } for i in range(1, 6)
                ],
                'analyzed_by': [
                    {
                        'name': request.form.get(f'analyzedBy{i}'),
                        'signature': request.form.get(f'analyzedSignature{i}')
                    } for i in range(1, 4)
                ],
                'checked_by': [
                    {
                        'name': request.form.get(f'checkedBy{i}'),
                        'signature': request.form.get(f'checkedSignature{i}')
                    } for i in range(1, 4)
                ],
                'created_by': username,  # Add created_by field
                'created_at': datetime.utcnow(),
                'edited_at': None
            }

            # Basic validation
            if not form_data['lab_number'] or not form_data['farm_location'] or not form_data['date_received'] or not form_data['date_reported']:
                flash('Please fill in all required metadata fields.', 'danger')
                return redirect(url_for('soil.soil'))

            if not form_data['analyzed_by'][0]['name'] or not form_data['checked_by'][0]['name']:
                flash('Please provide at least one Analyzed By and Checked By name.', 'danger')
                return redirect(url_for('soil.soil'))

            # Ensure at least one sample has data
            has_sample_data = False
            for sample in form_data['samples']:
                for key, value in sample.items():
                    if key in ['field', 'sample_ref', 'lab_no'] and value:
                        has_sample_data = True
                        break
                    if isinstance(value, dict) and (value['value'] is not None or value['class']):
                        has_sample_data = True
                        break
                if has_sample_data:
                    break
            if not has_sample_data:
                flash('Please provide data for at least one sample.', 'danger')
                return redirect(url_for('soil.soil'))

            # Insert into MongoDB
            result = soil_analysis_form_collection.insert_one(form_data)
            if result.inserted_id:
                flash('Soil analysis report submitted successfully!', 'success')
                return redirect(url_for('my_files.files'))  # Redirect to My Files
            else:
                flash('Failed to submit the report. Please try again.', 'danger')

        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'danger')
            return redirect(url_for('soil.soil', role = role))

    return render_template('soil_analysis_form.html')

@bp.route('/soil/view/<id>', methods=['GET'])
def view_soil(id):
    role = session.get('role', 'normal')
    try:
        worksheet = soil_analysis_form_collection.find_one({'_id': ObjectId(id)})
        if not worksheet:
            flash('Worksheet not found.', 'danger')
            return redirect(url_for('my_files.files'))
        return render_template('view_soil_analysis_form.html', worksheet=worksheet, role = role)
    except Exception as e:
        flash(f'Error retrieving worksheet: {str(e)}', 'danger')
        return redirect(url_for('my_files.files'))

@bp.route('/soil/edit/<id>', methods=['POST'])
def edit_soil(id):
    try:
        username = session.get('username')
        if not username:
            flash('Please log in to edit a soil analysis report.', 'danger')
            return redirect(url_for('login.login'))

        # Collect form data
        form_data = {
            'lab_number': request.form.get('labNumber'),
            'farm_location': request.form.get('farmLocation'),
            'date_received': request.form.get('dateReceived'),
            'date_reported': request.form.get('dateReported'),
            'samples': [
                {
                    'field': request.form.get(f'field{i}'),
                    'sample_ref': request.form.get(f'sampleRef{i}'),
                    'soil_depth': float(request.form.get(f'soilDepth{i}', 0)) if request.form.get(f'soilDepth{i}') else None,
                    'lab_no': request.form.get(f'labNo{i}'),
                    'texture': {
                        'value': request.form.get(f'textureValue{i}'),
                        'class': request.form.get(f'textureClass{i}')
                    },
                    'ph': {
                        'value': float(request.form.get(f'phValue{i}', 0)) if request.form.get(f'phValue{i}') else None,
                        'class': request.form.get(f'phClass{i}')
                    },
                    'conductivity': {
                        'value': float(request.form.get(f'conductivityValue{i}', 0)) if request.form.get(f'conductivityValue{i}') else None,
                        'class': request.form.get(f'conductivityClass{i}')
                    },
                    'org_carbon': {
                        'value': float(request.form.get(f'orgCarbonValue{i}', 0)) if request.form.get(f'orgCarbonValue{i}') else None,
                        'class': request.form.get(f'orgCarbonClass{i}')
                    },
                    'nitrogen': {
                        'value': float(request.form.get(f'nitrogenValue{i}', 0)) if request.form.get(f'nitrogenValue{i}') else None,
                        'class': request.form.get(f'nitrogenClass{i}')
                    },
                    'phosphorus_bray': {
                        'value': float(request.form.get(f'phosphorusBrayValue{i}', 0)) if request.form.get(f'phosphorusBrayValue{i}') else None,
                        'class': request.form.get(f'phosphorusBrayClass{i}')
                    },
                    'phosphorus_olsen': {
                        'value': request.form.get(f'phosphorusOlsenValue{i}'),
                        'class': request.form.get(f'phosphorusOlsenClass{i}')
                    },
                    'potassium': {
                        'value': float(request.form.get(f'potassiumValue{i}', 0)) if request.form.get(f'potassiumValue{i}') else None,
                        'class': request.form.get(f'potassiumClass{i}')
                    },
                    'calcium': {
                        'value': float(request.form.get(f'calciumValue{i}', 0)) if request.form.get(f'calciumValue{i}') else None,
                        'class': request.form.get(f'calciumClass{i}')
                    },
                    'magnesium': {
                        'value': float(request.form.get(f'magnesiumValue{i}', 0)) if request.form.get(f'magnesiumValue{i}') else None,
                        'class': request.form.get(f'magnesiumClass{i}')
                    },
                    'copper': {
                        'value': float(request.form.get(f'copperValue{i}', 0)) if request.form.get(f'copperValue{i}') else None,
                        'class': request.form.get(f'copperClass{i}')
                    },
                    'manganese': {
                        'value': float(request.form.get(f'manganeseValue{i}', 0)) if request.form.get(f'manganeseValue{i}') else None,
                        'class': request.form.get(f'manganeseClass{i}')
                    },
                    'iron': {
                        'value': float(request.form.get(f'ironValue{i}', 0)) if request.form.get(f'ironValue{i}') else None,
                        'class': request.form.get(f'ironClass{i}')
                    },
                    'zinc': {
                        'value': float(request.form.get(f'zincValue{i}', 0)) if request.form.get(f'zincValue{i}') else None,
                        'class': request.form.get(f'zincClass{i}')
                    }
                } for i in range(1, 6)
            ],
            'analyzed_by': [
                {
                    'name': request.form.get(f'analyzedBy{i}'),
                    'signature': request.form.get(f'analyzedSignature{i}')
                } for i in range(1, 4)
            ],
            'checked_by': [
                {
                    'name': request.form.get(f'checkedBy{i}'),
                    'signature': request.form.get(f'checkedSignature{i}')
                } for i in range(1, 4)
            ],
            'created_by': username,  # Ensure created_by is preserved
            'edited_at': datetime.utcnow()
        }

        # Basic validation
        if not form_data['lab_number'] or not form_data['farm_location'] or not form_data['date_received'] or not form_data['date_reported']:
            flash('Please fill in all required metadata fields.', 'danger')
            return redirect(url_for('soil.view_soil', id=id))

        if not form_data['analyzed_by'][0]['name'] or not form_data['checked_by'][0]['name']:
            flash('Please provide at least one Analyzed By and Checked By name.', 'danger')
            return redirect(url_for('soil.view_soil', id=id))

        # Ensure at least one sample has data
        has_sample_data = False
        for sample in form_data['samples']:
            for key, value in sample.items():
                if key in ['field', 'sample_ref', 'lab_no'] and value:
                    has_sample_data = True
                    break
                if isinstance(value, dict) and (value['value'] is not None or value['class']):
                    has_sample_data = True
                    break
            if has_sample_data:
                break
        if not has_sample_data:
            flash('Please provide data for at least one sample.', 'danger')
            return redirect(url_for('soil.view_soil', id=id))

        # Update in MongoDB
        result = soil_analysis_form_collection.update_one(
            {'_id': ObjectId(id)},
            {'$set': form_data}
        )
        if result.modified_count > 0:
            flash('Soil analysis report updated successfully!', 'success')
            return redirect(url_for('my_files.files'))  # Redirect to My Files
        else:
            flash('No changes made or worksheet not found.', 'danger')
            return redirect(url_for('soil.view_soil', id=id))

    except Exception as e:
        flash(f'Error updating worksheet: {str(e)}', 'danger')
        return redirect(url_for('soil.view_soil', id=id))
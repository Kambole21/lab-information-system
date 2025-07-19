from flask import Blueprint, render_template, flash, request, redirect, url_for, Response, session
from app import water_analysis_collection, water_analysis_versions_collection, user_collection, audit_log_collection
from bson import ObjectId
from datetime import datetime
import csv
import io
import logging
import pymongo
import traceback

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

bp = Blueprint('water_analysis', __name__)

@bp.route('/water_analysis', methods=['GET', 'POST'])
def water_analysis():
    role = session.get('role', 'normal')
    worksheet = None

    default_sample = {
        'sample_ref': '',
        'lab_num': '',
        'pH': '',
        'conductivity': '',
        'tds': '',
        'resistivity': '',
        'salinity': '',
        'sodium': '',
        'potassium': '',
        'calcium': '',
        'magnesium': '',
        'carbonates': '',
        'bicarbonates': '',
        'chlorides': '',
        'sulphates': '',
        'sar': '',
        'salinity_class': ''
    }

    if request.args.get('id'):
        try:
            worksheet = water_analysis_collection.find_one({'_id': ObjectId(request.args.get('id'))})
            if not worksheet:
                logger.error(f"Worksheet with ID {request.args.get('id')} not found.")
                flash('Worksheet not found.', 'danger')
                return redirect(url_for('submit.submit'))
            worksheet_samples = worksheet.get('samples', [])
            worksheet['samples'] = [dict(default_sample, **(sample if sample else {})) for sample in worksheet_samples] + \
                                   [dict(default_sample) for _ in range(4 - len(worksheet_samples))] if len(worksheet_samples) < 4 else worksheet_samples[:4]
        except Exception as e:
            logger.error(f"Error fetching worksheet: {str(e)}")
            flash(f'Error fetching worksheet: {str(e)}', 'danger')
            return redirect(url_for('submit.submit'))
    else:
        worksheet = {
            'lab_number': '',
            'farm_location': '',
            'date_received': '',
            'date_reported': '',
            'samples': [dict(default_sample) for _ in range(4)],
            'analyzed_by': '',
            'analyzed_signature': '',
            'checked_by': '',
            'checked_signature': '',
            'comment': '',
            'collection': 'Water Analysis Report'
        }

    if request.method == 'POST':
        try:
            logger.debug("Received POST request for water_analysis")
            form_data = {
                'lab_number': request.form.get('labNumber') or '',
                'farm_location': request.form.get('farmLocation') or '',
                'date_received': request.form.get('dateReceived') or '',
                'date_reported': request.form.get('dateReported') or '',
                'samples': [
                    {
                        'sample_ref': request.form.get(f'sampleRef{i}') or '',
                        'lab_num': request.form.get(f'labNum{i}') or '',
                        'pH': request.form.get(f'pH{i}') or '',
                        'conductivity': request.form.get(f'conductivity{i}') or '',
                        'tds': request.form.get(f'tds{i}') or '',
                        'resistivity': request.form.get(f'resistivity{i}') or '',
                        'salinity': request.form.get(f'salinity{i}') or '',
                        'sodium': request.form.get(f'sodium{i}') or '',
                        'potassium': request.form.get(f'potassium{i}') or '',
                        'calcium': request.form.get(f'calcium{i}') or '',
                        'magnesium': request.form.get(f'magnesium{i}') or '',
                        'carbonates': request.form.get(f'carbonates{i}') or '',
                        'bicarbonates': request.form.get(f'bicarbonates{i}') or '',
                        'chlorides': request.form.get(f'chlorides{i}') or '',
                        'sulphates': request.form.get(f'sulphates{i}') or '',
                        'sar': request.form.get(f'sar{i}') or '',
                        'salinity_class': request.form.get(f'salinityClass{i}') or ''
                    } for i in range(1, 5)
                ],
                'analyzed_by': request.form.get('analyzedBy') or '',
                'analyzed_signature': request.form.get('analyzedSignature') or '',
                'checked_by': request.form.get('checkedBy') or '',
                'checked_signature': request.form.get('checkedSignature') or '',
                'comment': request.form.get('comment') or '',
                'created_at': datetime.utcnow(),
                'created_by': session.get('username', 'Unknown'),
                'collection': 'Water Analysis Report'
            }

            logger.debug(f"Form data: {form_data}")

            if not form_data['lab_number'] or not form_data['farm_location'] or not form_data['date_received'] or not form_data['date_reported']:
                logger.warning("Required fields missing in form submission.")
                flash('Please fill in all required fields (Lab#, Location of Farm, Date Received, Date Reported).', 'danger')
                return render_template('water_analysis.html', worksheet=worksheet)

            has_sample_data = any(
                any(sample[key] for key in sample if key not in ['sample_ref', 'lab_num', 'salinity_class'])
                for sample in form_data['samples']
            )
            if not has_sample_data:
                logger.warning("No sample data provided.")
                flash('At least one sample must have data.', 'danger')
                return render_template('water_analysis.html', worksheet=worksheet)

            if request.form.get('id'):
                logger.info(f"Updating worksheet with ID: {request.form.get('id')}")
                form_data['edited_at'] = datetime.utcnow()
                result = water_analysis_collection.update_one(
                    {'_id': ObjectId(request.form.get('id'))},
                    {'$set': form_data}
                )
                if result.modified_count:
                    logger.info("Worksheet updated successfully.")
                    flash('Water analysis report updated successfully!', 'success')
                else:
                    logger.warning("No changes made to the worksheet.")
                    flash('No changes made to the report.', 'warning')
            else:
                logger.info("Inserting new worksheet.")
                result = water_analysis_collection.insert_one(form_data)
                if result.inserted_id:
                    logger.info(f"Worksheet inserted successfully with ID: {result.inserted_id}")
                    flash('Water analysis report submitted successfully!', 'success')
                else:
                    logger.error("Failed to insert worksheet.")
                    flash('Failed to submit the report. Please try again.', 'danger')

            return redirect(url_for('submit.submit'))

        except Exception as e:
            logger.error(f"Error processing form submission: {str(e)}")
            flash(f'An error occurred: {str(e)}', 'danger')
            return render_template('water_analysis.html', worksheet=worksheet, role = role)

    return render_template('water_analysis.html', worksheet=worksheet)

@bp.route('/view_water_analysis/<id>', methods=['GET'])
def view_water_analysis(id):
    role = session.get('role', 'normal')
    try:
        worksheet = water_analysis_collection.find_one({'_id': ObjectId(id)})
        if not worksheet:
            logger.error(f"Worksheet with ID {id} not found.")
            flash('Worksheet not found.', 'danger')
            return redirect(url_for('submit.submit'))
        user = user_collection.find_one({'username': session.get('username', 'Unknown')})
        if not user:
            logger.warning(f"No user found for username: {session.get('username', 'Unknown')}")
            flash('User profile not found.', 'warning')
        return render_template('view_water_analysis.html', worksheet=worksheet, user=user, role = role)
    except Exception as e:
        logger.error(f"Error fetching worksheet: {str(e)}")
        flash(f'Error fetching worksheet: {str(e)}', 'danger')
        return redirect(url_for('submit.submit'))

@bp.route('/edit_water_analysis/<id>', methods=['GET', 'POST'])
def edit_water_analysis(id):
    role = session.get('role', 'normal')
    default_sample = {
        'sample_ref': '',
        'lab_num': '',
        'pH': '',
        'conductivity': '',
        'tds': '',
        'resistivity': '',
        'salinity': '',
        'sodium': '',
        'potassium': '',
        'calcium': '',
        'magnesium': '',
        'carbonates': '',
        'bicarbonates': '',
        'chlorides': '',
        'sulphates': '',
        'sar': '',
        'salinity_class': ''
    }

    try:
        worksheet = water_analysis_collection.find_one({'_id': ObjectId(id)})
        if not worksheet:
            logger.error(f"Worksheet with ID {id} not found.")
            flash('Worksheet not found.', 'danger')
            return redirect(url_for('my_files.files'))

        worksheet_samples = worksheet.get('samples', [])
        worksheet['samples'] = [dict(default_sample, **(sample if sample else {})) for sample in worksheet_samples] + \
                              [dict(default_sample) for _ in range(4 - len(worksheet_samples))] if len(worksheet_samples) < 4 else worksheet_samples[:4]

        if request.method == 'POST':
            try:
                # Save current version before updating
                version_data = worksheet.copy()
                version_data['original_id'] = ObjectId(id)
                version_data['version_created_at'] = worksheet.get('edited_at', worksheet.get('created_at', datetime.utcnow()))
                version_data['version_saved_at'] = datetime.utcnow()
                version_data['version_number'] = water_analysis_versions_collection.count_documents({'original_id': ObjectId(id)}) + 1
                version_data['version_created_by'] = session.get('username', worksheet.get('created_by', 'Unknown'))
                version_data['collection'] = worksheet.get('collection', 'Water Analysis Report')
                
                # Remove the original _id to allow MongoDB to create a new one
                if '_id' in version_data:
                    version_data['_id'] = ObjectId()

                # Insert the version
                water_analysis_versions_collection.insert_one(version_data)

                # Proceed with the update
                form_data = {
                    'lab_number': request.form.get('labNumber') or '',
                    'farm_location': request.form.get('farmLocation') or '',
                    'date_received': request.form.get('dateReceived') or '',
                    'date_reported': request.form.get('dateReported') or '',
                    'samples': [
                        {
                            'sample_ref': request.form.get(f'sampleRef{i}') or '',
                            'lab_num': request.form.get(f'labNum{i}') or '',
                            'pH': request.form.get(f'pH{i}') or '',
                            'conductivity': request.form.get(f'conductivity{i}') or '',
                            'tds': request.form.get(f'tds{i}') or '',
                            'resistivity': request.form.get(f'resistivity{i}') or '',
                            'salinity': request.form.get(f'salinity{i}') or '',
                            'sodium': request.form.get(f'sodium{i}') or '',
                            'potassium': request.form.get(f'potassium{i}') or '',
                            'calcium': request.form.get(f'calcium{i}') or '',
                            'magnesium': request.form.get(f'magnesium{i}') or '',
                            'carbonates': request.form.get(f'carbonates{i}') or '',
                            'bicarbonates': request.form.get(f'bicarbonates{i}') or '',
                            'chlorides': request.form.get(f'chlorides{i}') or '',
                            'sulphates': request.form.get(f'sulphates{i}') or '',
                            'sar': request.form.get(f'sar{i}') or '',
                            'salinity_class': request.form.get(f'salinityClass{i}') or ''
                        } for i in range(1, 5)
                    ],
                    'analyzed_by': request.form.get('analyzedBy') or '',
                    'analyzed_signature': request.form.get('analyzedSignature') or '',
                    'checked_by': request.form.get('checkedBy') or '',
                    'checked_signature': request.form.get('checkedSignature') or '',
                    'comment': request.form.get('comment') or '',
                    'created_by': worksheet.get('created_by', session.get('username', 'Unknown')),
                    'created_at': worksheet.get('created_at', datetime.utcnow()),
                    'edited_at': datetime.utcnow(),
                    'collection': worksheet.get('collection', 'Water Analysis Report')
                }

                # Validate and update as before
                if not form_data['lab_number'] or not form_data['farm_location'] or not form_data['date_received'] or not form_data['date_reported']:
                    flash('Please fill in all required fields (Lab#, Location of Farm, Date Received, Date Reported).', 'danger')
                    return render_template('water_analysis.html', worksheet=worksheet, role=role)

                has_sample_data = any(
                    any(sample[key] for key in sample if key not in ['sample_ref', 'lab_num', 'salinity_class'])
                    for sample in form_data['samples']
                )
                if not has_sample_data:
                    flash('At least one sample must have data.', 'danger')
                    return render_template('water_analysis.html', worksheet=worksheet, role=role)

                result = water_analysis_collection.update_one(
                    {'_id': ObjectId(id)},
                    {'$set': form_data}
                )
                if result.modified_count:
                    flash('Water analysis report updated successfully! Version saved.', 'success')
                else:
                    flash('No changes made to the report.', 'warning')

                return redirect(url_for('my_files.files'))

            except Exception as e:
                logger.error(f"Error updating worksheet ID {id}: {str(e)}\n{traceback.format_exc()}")
                flash(f'An error occurred: {str(e)}', 'danger')
                return render_template('water_analysis.html', worksheet=worksheet, role=role)

        return render_template('water_analysis.html', worksheet=worksheet, role=role)

    except Exception as e:
        logger.error(f"Error fetching worksheet for edit: {str(e)}\n{traceback.format_exc()}")
        flash(f'Error fetching worksheet: {str(e)}', 'danger')
        return redirect(url_for('my_files.files'))

@bp.route('/test_version_insert/<id>', methods=['GET'])
def test_version_insert(id):
    try:
        logger.debug(f"Testing version insert for worksheet ID: {id}")
        worksheet = water_analysis_collection.find_one({'_id': ObjectId(id)})
        if not worksheet:
            logger.error(f"Worksheet with ID {id} not found.")
            flash('Worksheet not found.', 'danger')
            return redirect(url_for('my_files.files'))

        # Verify MongoDB connection
        try:
            water_analysis_versions_collection.database.command('ping')
            logger.debug("MongoDB connection is active")
            water_analysis_versions_collection.count_documents({}, limit=1)
            logger.debug("water_analysis_versions_collection is accessible")
        except pymongo.errors.ConnectionError as e:
            logger.error(f"MongoDB connection failure: {str(e)}\n{traceback.format_exc()}")
            audit_log_collection.insert_one({
                'user_id': session.get('user_id', 'Unknown'),
                'email': session.get('email', 'Unknown'),
                'event_type': 'test_version_save_failure',
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'worksheet_id': id,
                'error': f"MongoDB connection failure: {str(e)}",
                'ip_address': request.remote_addr
            })
            flash(f'Version history database is inaccessible: {str(e)}', 'danger')
            return redirect(url_for('my_files.files'))

        # Prepare version data
        version_data = worksheet.copy()
        version_data['original_id'] = ObjectId(id)
        version_data['version_created_at'] = worksheet.get('edited_at', worksheet.get('created_at', datetime.utcnow()))
        version_data['version_saved_at'] = datetime.utcnow()
        version_data['version_number'] = water_analysis_versions_collection.count_documents({'original_id': ObjectId(id)}) + 1
        version_data['version_created_by'] = session.get('username', worksheet.get('created_by', 'Unknown'))
        version_data['collection'] = worksheet.get('collection', 'Water Analysis Report')

        if '_id' in version_data:
            version_data['_id'] = ObjectId()

        # Validate version_data
        required_fields = ['original_id', 'version_number', 'version_created_at', 'version_saved_at', 'version_created_by', 'collection']
        missing_fields = [field for field in required_fields if field not in version_data or version_data[field] is None]
        if missing_fields:
            logger.error(f"Test version data missing required fields: {missing_fields}")
            audit_log_collection.insert_one({
                'user_id': session.get('user_id', 'Unknown'),
                'email': session.get('email', 'Unknown'),
                'event_type': 'test_version_save_failure',
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'worksheet_id': id,
                'error': f"Missing fields: {missing_fields}",
                'ip_address': request.remote_addr
            })
            flash(f'Failed to save test version due to missing fields: {missing_fields}', 'danger')
            return redirect(url_for('my_files.files'))

        # Log version attempt
        logger.debug(f"Test version data to be saved: {version_data}")
        audit_log_collection.insert_one({
            'user_id': session.get('user_id', 'Unknown'),
            'email': session.get('email', 'Unknown'),
            'event_type': 'test_version_save_attempt',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'worksheet_id': id,
            'version_number': version_data['version_number'],
            'ip_address': request.remote_addr
        })

        # Insert version and verify
        result = water_analysis_versions_collection.insert_one(version_data)
        if not result.inserted_id:
            logger.error(f"Failed to save test version for worksheet ID {id}: No inserted_id returned")
            audit_log_collection.insert_one({
                'user_id': session.get('user_id', 'Unknown'),
                'email': session.get('email', 'Unknown'),
                'event_type': 'test_version_save_failure',
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'worksheet_id': id,
                'version_number': version_data['version_number'],
                'error': 'No inserted_id returned',
                'ip_address': request.remote_addr
            })
            flash('Failed to save test version. Please try again or contact support.', 'danger')
            return redirect(url_for('my_files.files'))

        saved_version = water_analysis_versions_collection.find_one({'_id': result.inserted_id})
        if not saved_version:
            logger.error(f"Test version {version_data['version_number']} for worksheet ID {id} was not found after insertion")
            audit_log_collection.insert_one({
                'user_id': session.get('user_id', 'Unknown'),
                'email': session.get('email', 'Unknown'),
                'event_type': 'test_version_save_failure',
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'worksheet_id': id,
                'version_number': version_data['version_number'],
                'error': 'Version not found after insertion',
                'ip_address': request.remote_addr
            })
            flash('Test version save failed verification. Please try again or contact support.', 'danger')
            return redirect(url_for('my_files.files'))

        logger.info(f"Saved test version {version_data['version_number']} for worksheet ID {id} with version ID {result.inserted_id}")
        audit_log_collection.insert_one({
            'user_id': session.get('user_id', 'Unknown'),
            'email': session.get('email', 'Unknown'),
            'event_type': 'test_version_save_success',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'worksheet_id': id,
            'version_number': version_data['version_number'],
            'version_id': str(result.inserted_id),
            'ip_address': request.remote_addr
        })
        flash(f'Test version {version_data["version_number"]} saved successfully for worksheet ID {id}.', 'success')
        return redirect(url_for('water_analysis.view_version_history', id=id))

    except Exception as e:
        logger.error(f"Error testing version insert for worksheet ID {id}: {str(e)}\n{traceback.format_exc()}")
        audit_log_collection.insert_one({
            'user_id': session.get('user_id', 'Unknown'),
            'email': session.get('email', 'Unknown'),
            'event_type': 'test_version_save_failure',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'worksheet_id': id,
            'error': f"{str(e)}",
            'stack_trace': traceback.format_exc(),
            'ip_address': request.remote_addr
        })
        flash(f'Error testing version insert: {str(e)}', 'danger')
        return redirect(url_for('my_files.files'))

@bp.route('/view_version_history/<id>', methods=['GET'])
def view_version_history(id):
    try:
        worksheet = water_analysis_collection.find_one({'_id': ObjectId(id)})
        if not worksheet:
            logger.error(f"Worksheet with ID {id} not found.")
            flash('Worksheet not found.', 'danger')
            return redirect(url_for('my_files.files'))

        versions = list(water_analysis_versions_collection.find({'original_id': ObjectId(id)}).sort('version_number', -1))
        logger.debug(f"Found {len(versions)} versions for worksheet ID {id}: {[str(v['_id']) for v in versions]}")
        if not versions:
            logger.info(f"No versions found for worksheet ID {id}")
            flash(f'No version history is available for this worksheet (ID: {id}). This may occur if the worksheet has not been edited yet or if version saving failed.', 'info')

        user = user_collection.find_one({'username': session.get('username', 'Unknown')})
        if not user:
            logger.warning(f"No user found for username: {session.get('username', 'Unknown')}")
            flash('User profile not found.', 'warning')

        return render_template('view_version_history.html', worksheet=worksheet, versions=versions, user=user)
    except Exception as e:
        logger.error(f"Error fetching version history for worksheet ID {id}: {str(e)}\n{traceback.format_exc()}")
        flash(f'Error fetching version history: {str(e)}', 'danger')
        return redirect(url_for('my_files.files'))

@bp.route('/download_csv/<id>', methods=['GET'])
def download_csv(id):
    try:
        worksheet = water_analysis_collection.find_one({'_id': ObjectId(id)})
        if not worksheet:
            logger.error(f"Worksheet with ID {id} not found for CSV download.")
            flash('Worksheet not found.', 'danger')
            return redirect(url_for('submit.submit'))

        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        headers = [
            'Lab Number', 'Farm Location', 'Date Received', 'Date Reported',
            'Sample 1 Ref', 'Sample 1 Lab #', 'Sample 1 pH', 'Sample 1 Conductivity (µS/cm)', 'Sample 1 TDS (mg/l)', 'Sample 1 Resistivity', 'Sample 1 Salinity (%)', 'Sample 1 Sodium (me/l)', 'Sample 1 Potassium (me/l)', 'Sample 1 Calcium (me/l)', 'Sample 1 Magnesium (me/l)', 'Sample 1 Carbonates (me/l)', 'Sample 1 Bicarbonates (me/l)', 'Sample 1 Chlorides (me/l)', 'Sample 1 Sulphates (me/l)', 'Sample 1 SAR', 'Sample 1 Salinity Class',
            'Sample 2 Ref', 'Sample 2 Lab #', 'Sample 2 pH', 'Sample 2 Conductivity (µS/cm)', 'Sample 2 TDS (mg/l)', 'Sample 2 Resistivity', 'Sample 2 Salinity (%)', 'Sample 2 Sodium (me/l)', 'Sample 2 Potassium (me/l)', 'Sample 2 Calcium (me/l)', 'Sample 2 Magnesium (me/l)', 'Sample 2 Carbonates (me/l)', 'Sample 2 Bicarbonates (me/l)', 'Sample 2 Chlorides (me/l)', 'Sample 2 Sulphates (me/l)', 'Sample 2 SAR', 'Sample 2 Salinity Class',
            'Sample 3 Ref', 'Sample 3 Lab #', 'Sample 3 pH', 'Sample 3 Conductivity (µS/cm)', 'Sample 3 TDS (mg/l)', 'Sample 3 Resistivity', 'Sample 3 Salinity (%)', 'Sample 3 Sodium (me/l)', 'Sample 3 Potassium (me/l)', 'Sample 3 Calcium (me/l)', 'Sample 3 Magnesium (me/l)', 'Sample 3 Carbonates (me/l)', 'Sample 3 Bicarbonates (me/l)', 'Sample 3 Chlorides (me/l)', 'Sample 3 Sulphates (me/l)', 'Sample 3 SAR', 'Sample 3 Salinity Class',
            'Sample 4 Ref', 'Sample 4 Lab #', 'Sample 4 pH', 'Sample 4 Conductivity (µS/cm)', 'Sample 4 TDS (mg/l)', 'Sample 4 Resistivity', 'Sample 4 Salinity (%)', 'Sample 4 Sodium (me/l)', 'Sample 4 Potassium (me/l)', 'Sample 4 Calcium (me/l)', 'Sample 4 Magnesium (me/l)', 'Sample 4 Carbonates (me/l)', 'Sample 4 Bicarbonates (me/l)', 'Sample 4 Chlorides (me/l)', 'Sample 4 Sulphates (me/l)', 'Sample 4 SAR', 'Sample 4 Salinity Class',
            'Analyzed By', 'Analyzed Signature', 'Checked By', 'Checked Signature', 'Comment'
        ]
        writer.writerow(headers)

        # Write data
        row = [
            worksheet.get('lab_number', ''),
            worksheet.get('farm_location', ''),
            worksheet.get('date_received', ''),
            worksheet.get('date_reported', '')
        ]
        for i in range(4):
            sample = worksheet.get('samples', [{}])[i]
            row.extend([
                sample.get('sample_ref', ''),
                sample.get('lab_num', ''),
                sample.get('pH', ''),
                sample.get('conductivity', ''),
                sample.get('tds', ''),
                sample.get('resistivity', ''),
                sample.get('salinity', ''),
                sample.get('sodium', ''),
                sample.get('potassium', ''),
                sample.get('calcium', ''),
                sample.get('magnesium', ''),
                sample.get('carbonates', ''),
                sample.get('bicarbonates', ''),
                sample.get('chlorides', ''),
                sample.get('sulphates', ''),
                sample.get('sar', ''),
                sample.get('salinity_class', '')
            ])
        row.extend([
            worksheet.get('analyzed_by', ''),
            worksheet.get('analyzed_signature', ''),
            worksheet.get('checked_by', ''),
            worksheet.get('checked_signature', ''),
            worksheet.get('comment', '')
        ])
        writer.writerow(row)

        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename=water_analysis_{worksheet.get("lab_number", "report")}.csv'}
        )
    except Exception as e:
        logger.error(f"Error generating CSV: {str(e)}\n{traceback.format_exc()}")
        flash(f'Error generating CSV: {str(e)}', 'danger')
        return redirect(url_for('submit.submit'))

@bp.route('/restore_version/<version_id>/<original_id>')
def restore_version(version_id, original_id):
    if session.get('role') not in ['superuser', 'ultra_superuser']:
        flash('You do not have permission to restore versions', 'danger')
        return redirect(url_for('water_analysis.view_version_history', id=original_id))

    try:
        # Get the version to restore
        version = water_analysis_versions_collection.find_one({'_id': ObjectId(version_id)})
        if not version:
            flash('Version not found', 'danger')
            return redirect(url_for('water_analysis.view_version_history', id=original_id))

        # Save current version as a new version before restoring
        current = water_analysis_collection.find_one({'_id': ObjectId(original_id)})
        if current:
            current_version_data = current.copy()
            current_version_data['original_id'] = ObjectId(original_id)
            current_version_data['version_created_at'] = current.get('edited_at', current.get('created_at', datetime.utcnow()))
            current_version_data['version_saved_at'] = datetime.utcnow()
            current_version_data['version_number'] = water_analysis_versions_collection.count_documents({'original_id': ObjectId(original_id)}) + 1
            current_version_data['version_created_by'] = session.get('username', current.get('created_by', 'Unknown'))
            current_version_data['collection'] = current.get('collection', 'Water Analysis Report')
            current_version_data['_id'] = ObjectId()
            water_analysis_versions_collection.insert_one(current_version_data)

        # Restore the selected version
        version_to_restore = version.copy()
        version_to_restore['_id'] = ObjectId(original_id)
        version_to_restore['edited_at'] = datetime.utcnow()
        
        # Remove version-specific fields
        for field in ['original_id', 'version_number', 'version_created_at', 'version_saved_at', 'version_created_by']:
            version_to_restore.pop(field, None)

        water_analysis_collection.replace_one({'_id': ObjectId(original_id)}, version_to_restore)
        
        flash('Version restored successfully', 'success')
        return redirect(url_for('water_analysis.view_water_analysis', id=original_id))

    except Exception as e:
        logger.error(f"Error restoring version: {str(e)}")
        flash(f'Error restoring version: {str(e)}', 'danger')
        return redirect(url_for('water_analysis.view_version_history', id=original_id))
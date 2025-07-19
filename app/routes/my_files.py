from flask import Blueprint, render_template, flash, session, redirect, url_for, jsonify
from app import water_analysis_collection, equipment_collection, trace_worksheet_collection, water_worksheet_collection, organic_carbon_nitrogent_collection, ph_trace_form_collection, soil_analysis_form_collection, user_collection
import logging
from datetime import datetime
from bson import ObjectId

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

bp = Blueprint('my_files', __name__)

@bp.route('/files')
def files():
    role = session.get('role', 'normal')
    username = session.get('username')
    logger.debug(f"Fetching files for username: {username}")
    if not username:
        flash('Please log in to view your files.', 'danger')
        return redirect(url_for('login.login'))

    user = user_collection.find_one({'username': username})
    if not user:
        logger.error(f"No user found for username: {username}")
        flash('User not found.', 'danger')
        return redirect(url_for('login.login'))

    worksheets = []
    for collection_name, collection in [
        ('Water Analysis Report', water_analysis_collection),
        ('Equipment Operation Log Book', equipment_collection),
        ('Trace Worksheet Form', trace_worksheet_collection),
        ('Water Analysis Worksheet', water_worksheet_collection),
        ('Organic Carbon & Nitrogen Worksheet', organic_carbon_nitrogent_collection),
        ('pH, Phosphorus, Bases & Traces Worksheet', ph_trace_form_collection),
        ('Soil Analysis Report Form', soil_analysis_form_collection)
    ]:
        for doc in collection.find({'created_by': username}):
            logger.debug(f"Found document in {collection_name}: {doc}")
            date = doc.get('created_at', datetime.utcnow()).strftime('%Y-%m-%d')
            created_by = doc.get('created_by', username)
            if collection_name == 'Equipment Operation Log Book':
                date = doc.get('log_entries', [{}])[0].get('date', date)
                created_by = doc.get('log_entries', [{}])[0].get('operator', created_by)
            elif collection_name == 'Trace Worksheet Form':
                date = doc.get('date_of_analysis', date)
                created_by = doc.get('analyzed_by', {}).get('name', created_by)
            elif collection_name == 'Water Analysis Worksheet':
                date = doc.get('date_checked', date)
                created_by = doc.get('analyzed_by', created_by)
            elif collection_name == 'Organic Carbon & Nitrogen Worksheet':
                date = doc.get('date', date)
                created_by = doc.get('analyzed_by', {}).get('name', created_by)
            elif collection_name == 'pH, Phosphorus, Bases & Traces Worksheet':
                date = doc.get('date_of_analysis', date)
                created_by = doc.get('analyzed_by', {}).get('name', created_by)
            elif collection_name == 'Soil Analysis Report Form':
                date = doc.get('date_received', date)
                created_by = doc.get('analyzed_by', [{}])[0].get('name', created_by)

            worksheets.append({
                'id': str(doc['_id']),
                'title': collection_name,
                'date': date,
                'created_by': created_by,
                'comment': doc.get('comment', ''),
                'collection': collection_name,
                'edited_at': doc.get('edited_at', '').strftime('%Y-%m-%d %H:%M:%S') if doc.get('edited_at') else ''
            })

    worksheets.sort(key=lambda x: x['date'], reverse=True)

    return render_template('my_files.html', worksheets=worksheets, user=user, role = role)

@bp.route('/delete_worksheet/<id>/<collection>', methods=['POST'])
def delete_worksheet(id, collection):
    try:
        collections_map = {
            'Water Analysis Report': water_analysis_collection,
            'Equipment Operation Log Book': equipment_collection,
            'Trace Worksheet Form': trace_worksheet_collection,
            'Water Analysis Worksheet': water_worksheet_collection,
            'Organic Carbon & Nitrogen Worksheet': organic_carbon_nitrogent_collection,
            'pH, Phosphorus, Bases & Traces Worksheet': ph_trace_form_collection,
            'Soil Analysis Report Form': soil_analysis_form_collection
        }
        collection_obj = collections_map.get(collection)
        if collection_obj is None:
            logger.error(f"Invalid collection: {collection}")
            return jsonify({'success': False, 'error': 'Invalid collection'}), 400

        username = session.get('username')
        if not username:
            logger.error("No user logged in for deletion attempt")
            return jsonify({'success': False, 'error': 'Please log in to delete worksheets.'}), 401

        worksheet = collection_obj.find_one({'_id': ObjectId(id)})
        if not worksheet:
            logger.error(f"Worksheet not found: ID {id} in collection {collection}")
            return jsonify({'success': False, 'error': 'Worksheet not found.'}), 404

        if worksheet.get('created_by') != username:
            logger.error(f"Unauthorized deletion attempt by {username} for worksheet ID {id}")
            return jsonify({'success': False, 'error': 'You are not authorized to delete this worksheet.'}), 403

        result = collection_obj.delete_one({'_id': ObjectId(id)})
        if result.deleted_count > 0:
            logger.info(f"Worksheet deleted successfully: ID {id} from {collection} by {username}")
            return jsonify({'success': True, 'message': 'Worksheet deleted successfully.'})
        else:
            logger.error(f"Failed to delete worksheet: ID {id} in {collection}")
            return jsonify({'success': False, 'error': 'Failed to delete worksheet.'}), 500

    except Exception as e:
        logger.error(f"Error deleting worksheet ID {id} from {collection}: {str(e)}")
        return jsonify({'success': False, 'error': f'Error deleting worksheet: {str(e)}'}), 500
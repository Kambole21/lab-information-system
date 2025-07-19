from flask import Blueprint, render_template, flash, request, jsonify, make_response, redirect, url_for, session
from app import water_worksheet_collection, organic_carbon_nitrogent_collection, ph_trace_form_collection, water_analysis_collection, trace_worksheet_collection, soil_analysis_form_collection, equipment_collection
from bson import ObjectId
from datetime import datetime
import csv
from io import StringIO

bp = Blueprint('submit', __name__)

@bp.route('/submission_page', methods=['GET', 'POST'])
def submit():
    role = session.get('role', 'normal')
    try:
        collections = [
            (water_worksheet_collection, "Water Analysis Worksheet"),
            (organic_carbon_nitrogent_collection, "Organic Carbon & Nitrogen Worksheet"),
            (ph_trace_form_collection, "pH, Phosphorus, Bases & Traces Worksheet"),
            (water_analysis_collection, "Water Analysis Report"),
            (trace_worksheet_collection, "Trace Worksheet Form"),
            (soil_analysis_form_collection, "Soil Analysis Report Form"),
            (equipment_collection, "Equipment Operation Log Book"),
        ]

        filter_title = request.form.get('title', '') if request.method == 'POST' else ''
        filter_creator = request.form.get('created_by', '') if request.method == 'POST' else ''
        filter_date = request.form.get('date', '') if request.method == 'POST' else ''

        worksheets = []
        for collection, title in collections:
            if filter_title and filter_title != title:
                continue

            try:
                query = {}
                if filter_creator:
                    query['$or'] = [
                        {'created_by': {'$regex': filter_creator, '$options': 'i'}},
                        {'analyzed_by': {'$regex': filter_creator, '$options': 'i'}},
                        {'analyzed_by.name': {'$regex': filter_creator, '$options': 'i'}},
                        {'log_entries.operator': {'$regex': filter_creator, '$options': 'i'}}
                    ]
                if filter_date:
                    try:
                        date_obj = datetime.strptime(filter_date, '%Y-%m-%d')
                        query['$or'] = query.get('$or', []) + [
                            {'created_at': {'$gte': date_obj, '$lt': date_obj.replace(hour=23, minute=59, second=59)}},
                            {'date': filter_date},
                            {'date_of_analysis': filter_date},
                            {'date_checked': filter_date},
                            {'log_entries.date': filter_date}
                        ]
                    except ValueError:
                        flash(f"Invalid date format provided: {filter_date}. Expected format is YYYY-MM-DD.", "warning")

                docs = collection.find(query)
                for doc in docs:
                    created_by = doc.get('created_by', session.get('username', 'Unknown'))
                    date = doc.get('date_of_analysis' if title in ["pH, Phosphorus, Bases & Traces Worksheet", "Trace Worksheet Form"] else 'date_checked' if title == "Water Analysis Worksheet" else 'date', doc.get('created_at', datetime.utcnow()).strftime('%Y-%m-%d'))
                    if title == "Equipment Operation Log Book":
                        created_by = doc.get('log_entries', [{}])[0].get('operator', created_by)
                        date = doc.get('log_entries', [{}])[0].get('date', date)
                    elif isinstance(doc.get('analyzed_by'), dict):
                        created_by = doc.get('analyzed_by', {}).get('name', created_by)

                    worksheets.append({
                        'id': str(doc.get('_id', '')),
                        'title': title,
                        'created_by': created_by,
                        'date': date,
                        'comment': doc.get('comment', ''),
                        'collection': title,
                        'edited_at': doc.get('edited_at', '').strftime('%Y-%m-%d %H:%M:%S') if doc.get('edited_at') else ''
                    })
            except Exception as e:
                flash(f'Error fetching from {title}: {str(e)}', 'danger')
                continue

        worksheets.sort(key=lambda x: x['date'], reverse=True)

        return render_template(
            'submit.html',
            worksheets=worksheets,
            filter_title=filter_title,
            filter_creator=filter_creator,
            filter_date=filter_date,
            role=role,
            collection_titles=[title for _, title in collections]
        )

    except Exception as e:
        flash(f'Error fetching worksheets: {str(e)}', 'danger')
        return render_template(
            'submit.html',
            worksheets=[],
            filter_title='',
            filter_creator='',
            filter_date='',
            role=role,
            collection_titles=[title for _, title in collections]
        )

@bp.route('/view_soil_analysis/<id>')
def view_soil_analysis(id):
    role = session.get('role', 'normal')
    try:
        worksheet = soil_analysis_form_collection.find_one({'_id': ObjectId(id)})
        if not worksheet:
            flash('Soil Analysis Report not found.', 'danger')
            return redirect(url_for('submit.submit'))
        return render_template('view_soil_analysis_form.html', worksheet=worksheet, role=role)
    except Exception as e:
        flash(f'Error fetching worksheet: {str(e)}', 'danger')
        return redirect(url_for('submit.submit'))

@bp.route('/view_water_worksheet/<id>')
def view_water_worksheet(id):
    role = session.get('role', 'normal')
    try:
        worksheet = water_worksheet_collection.find_one({'_id': ObjectId(id)})
        if not worksheet:
            flash('Water Analysis Worksheet not found.', 'danger')
            return redirect(url_for('submit.submit'))
        return render_template('view_water_worksheet.html', worksheet=worksheet, role=role)
    except Exception as e:
        flash(f'Error fetching worksheet: {str(e)}', 'danger')
        return redirect(url_for('submit.submit'))

@bp.route('/view_ocn/<id>')
def view_ocn(id):
    role = session.get('role', 'normal')
    try:
        worksheet = organic_carbon_nitrogent_collection.find_one({'_id': ObjectId(id)})
        if not worksheet:
            flash('Organic Carbon & Nitrogen Worksheet not found.', 'danger')
            return redirect(url_for('submit.submit'))
        return render_template('view_ocn.html', worksheet=worksheet, role=role)
    except Exception as e:
        flash(f'Error fetching worksheet: {str(e)}', 'danger')
        return redirect(url_for('submit.submit'))

@bp.route('/view_ph/<id>')
def view_ph(id):
    role = session.get('role', 'normal')
    try:
        worksheet = ph_trace_form_collection.find_one({'_id': ObjectId(id)})
        if not worksheet:
            flash('pH, Phosphorus, Bases & Traces Worksheet not found.', 'danger')
            return redirect(url_for('submit.submit'))
        return render_template('view_ph.html', worksheet=worksheet, role=role)
    except Exception as e:
        flash(f'Error fetching worksheet: {str(e)}', 'danger')
        return redirect(url_for('submit.submit'))

@bp.route('/download_water_worksheet_csv/<id>')
def download_water_worksheet_csv(id):
    role = session.get('role', 'normal')
    try:
        worksheet = water_worksheet_collection.find_one({'_id': ObjectId(id)})
        if not worksheet:
            flash('Water Analysis Worksheet not found.', 'danger')
            return redirect(url_for('submit.submit'))

        output = StringIO()
        writer = csv.writer(output)
        writer.writerow([
            'Sample Number', 'Lab No.', 'pH', 'EC (µS/cm)', 'TDS (ppm)', 'Resistivity', 'Salinity (%)',
            'CO₃²⁻ (mg/l)', 'HCO₃⁻ (mg/l)', 'Cl⁻ (mg/l)', 'SO₄²⁻ (mg/l)', 'K⁺ (mg/l)', 'Ca²⁺ (mg/l)',
            'Mg²⁺ (mg/l)', 'Na⁺ (mg/l)', 'Cu²⁺ (mg/l)', 'Mn²⁺ (mg/l)', 'Fe²⁺ (mg/l)', 'Zn²⁺ (mg/l)'
        ])

        for sample in worksheet.get('samples', []):
            writer.writerow([
                sample.get('sample_number', ''),
                sample.get('lab_no', ''),
                sample.get('ph', ''),
                sample.get('ec', ''),
                sample.get('tds', ''),
                sample.get('resistivity', ''),
                sample.get('salinity', ''),
                sample.get('co3', ''),
                sample.get('hco3', ''),
                sample.get('cl', ''),
                sample.get('so4', ''),
                sample.get('k', ''),
                sample.get('ca', ''),
                sample.get('mg', ''),
                sample.get('na', ''),
                sample.get('cu', ''),
                sample.get('mn', ''),
                sample.get('fe', ''),
                sample.get('zn', '')
            ])

        output.seek(0)
        response = make_response(output.getvalue())
        response.headers['Content-Disposition'] = f'attachment; filename=water_worksheet_{id}.csv'
        response.headers['Content-Type'] = 'text/csv'
        return response
    except Exception as e:
        flash(f'Error generating CSV: {str(e)}', 'danger')
        return redirect(url_for('submit.submit'))

@bp.route('/download_ocn_csv/<id>')
def download_ocn_csv(id):
    role = session.get('role', 'normal')
    try:
        worksheet = organic_carbon_nitrogent_collection.find_one({'_id': ObjectId(id)})
        if not worksheet:
            flash('Organic Carbon & Nitrogen Worksheet not found.', 'danger')
            return redirect(url_for('submit.submit'))

        output = StringIO()
        writer = csv.writer(output)
        writer.writerow([
            'Table', 'Serial Number', 'Lab No.', 'Initial Volume (ml)', 'Titre Volume (ml)', 'Final Volume (ml)'
        ])

        for table_name, table_data in [('Left Table', worksheet.get('left_table', [])), ('Right Table', worksheet.get('right_table', []))]:
            for row in table_data:
                writer.writerow([
                    table_name,
                    row.get('serial_number', ''),
                    row.get('lab_no', ''),
                    row.get('ini_vol', ''),
                    row.get('titre_vol', ''),
                    row.get('final_vol', '')
                ])

        output.seek(0)
        response = make_response(output.getvalue())
        response.headers['Content-Disposition'] = f'attachment; filename=ocn_worksheet_{id}.csv'
        response.headers['Content-Type'] = 'text/csv'
        return response
    except Exception as e:
        flash(f'Error generating CSV: {str(e)}', 'danger')
        return redirect(url_for('submit.submit'))

@bp.route('/download_ph_csv/<id>')
def download_ph_csv(id):
    role = session.get('role', 'normal')
    try:
        worksheet = ph_trace_form_collection.find_one({'_id': ObjectId(id)})
        if not worksheet:
            flash('pH, Phosphorus, Bases & Traces Worksheet not found.', 'danger')
            return redirect(url_for('submit.submit'))

        output = StringIO()
        writer = csv.writer(output)

        writer.writerow(['Calibration Table'])
        writer.writerow([
            'S/N', 'P Std Conc', 'P Abs Reading', 'K Std Conc', 'K Abs Reading', 'Ca Std Conc', 'Ca Abs Reading',
            'Mg Std Conc', 'Mg Abs Reading', 'Na Std Conc', 'Na Abs Reading'
        ])
        for row in worksheet.get('calibration_table', []):
            writer.writerow([
                row.get('serial_number', ''),
                row.get('p_std_conc', ''),
                row.get('p_abs_reading', ''),
                row.get('k_std_conc', ''),
                row.get('k_abs_reading', ''),
                row.get('ca_std_conc', ''),
                row.get('ca_abs_reading', ''),
                row.get('mg_std_conc', ''),
                row.get('mg_abs_reading', ''),
                row.get('na_std_conc', ''),
                row.get('na_abs_reading', '')
            ])

        writer.writerow(['Analysis Table'])
        writer.writerow([
            'S/N', 'Lab No.', 'pH (CaCl₂)', 'P Instrument Reading', 'P D.F', 'P mg/l',
            'K Instrument Reading', 'K D.F', 'K mg/l', 'Ca Instrument Reading', 'Ca D.F', 'Ca mg/l',
            'Mg Instrument Reading', 'Mg D.F', 'Mg mg/l', 'Na Instrument Reading', 'Na D.F', 'Na mg/l'
        ])
        for row in worksheet.get('analysis_table', []):
            writer.writerow([
                row.get('serial_number', ''),
                row.get('lab_no', ''),
                row.get('ph_cacl2', ''),
                row.get('p_instrument_reading', ''),
                row.get('p_df', ''),
                row.get('p_mgl', ''),
                row.get('k_instrument_reading', ''),
                row.get('k_df', ''),
                row.get('k_mgl', ''),
                row.get('ca_instrument_reading', ''),
                row.get('ca_df', ''),
                row.get('ca_mgl', ''),
                row.get('mg_instrument_reading', ''),
                row.get('mg_df', ''),
                row.get('mg_mgl', ''),
                row.get('na_instrument_reading', ''),
                row.get('na_df', ''),
                row.get('na_mgl', '')
            ])

        output.seek(0)
        response = make_response(output.getvalue())
        response.headers['Content-Disposition'] = f'attachment; filename=ph_worksheet_{id}.csv'
        response.headers['Content-Type'] = 'text/csv'
        return response
    except Exception as e:
        flash(f'Error generating CSV: {str(e)}', 'danger')
        return redirect(url_for('submit.submit'))

@bp.route('/view/<id>/<collection>')
def view_worksheet(id, collection):
    try:
        collections_map = {
            'Water Analysis Worksheet': water_worksheet_collection,
            'Organic Carbon & Nitrogen Worksheet': organic_carbon_nitrogent_collection,
            'pH, Phosphorus, Bases & Traces Worksheet': ph_trace_form_collection,
            'Water Analysis Report': water_analysis_collection,
            'Trace Worksheet Form': trace_worksheet_collection,
            'Soil Analysis Report Form': soil_analysis_form_collection,
            'Equipment Operation Log Book': equipment_collection
        }
        collection_obj = collections_map.get(collection)
        if collection_obj is None:
            return jsonify({'error': 'Invalid collection'}), 400

        doc = collection_obj.find_one({'_id': ObjectId(id)})
        if doc is None:
            return jsonify({'error': 'Worksheet not found'}), 404

        if collection == 'Equipment Operation Log Book':
            worksheet_data = {
                'id': str(doc.get('_id', '')),
                'title': collection,
                'equipment_name': doc.get('equipment_name', ''),
                'location': doc.get('location', ''),
                'model_no': doc.get('model_no', ''),
                'serial_no': doc.get('serial_no', ''),
                'manufacturer': doc.get('manufacturer', ''),
                'created_by': doc.get('created_by', session.get('username', 'Unknown')),
                'edited_at': doc.get('edited_at', '').strftime('%Y-%m-%d %H:%M:%S') if doc.get('edited_at') else '',
                'log_entries': [
                    {
                        'serial_number': entry.get('serial_number', ''),
                        'date': entry.get('date', ''),
                        'operator': entry.get('operator', ''),
                        'analysis_done': entry.get('analysis_done', ''),
                        'no_of_samples': entry.get('no_of_samples', ''),
                        'instrument_performance': entry.get('instrument_performance', '')
                    } for entry in doc.get('log_entries', [])
                ],
                'created_at': doc.get('created_at', datetime.utcnow()).strftime('%Y-%m-%d'),
                'comment': doc.get('comment', '')
            }
        elif collection == 'Water Analysis Worksheet':
            worksheet_data = {
                'id': str(doc.get('_id', '')),
                'title': collection,
                'lab_number': '',
                'analyzed_by': doc.get('analyzed_by', ''),
                'analyzed_by_date': doc.get('date_checked', ''),
                'checked_by': doc.get('checked_by', ''),
                'checked_by_date': doc.get('date_checked', ''),
                'created_by': doc.get('created_by', session.get('username', 'Unknown')),
                'edited_at': doc.get('edited_at', '').strftime('%Y-%m-%d %H:%M:%S') if doc.get('edited_at') else '',
                'date': doc.get('date_checked', doc.get('created_at', datetime.utcnow()).strftime('%Y-%m-%d')),
                'comment': doc.get('comment', ''),
                'samples': [
                    {
                        'sample_number': sample.get('sample_number', ''),
                        'lab_no': sample.get('lab_no', ''),
                        'ph': sample.get('ph', ''),
                        'ec': sample.get('ec', ''),
                        'tds': sample.get('tds', ''),
                        'resistivity': sample.get('resistivity', ''),
                        'salinity': sample.get('salinity', ''),
                        'co3': sample.get('co3', ''),
                        'hco3': sample.get('hco3', ''),
                        'cl': sample.get('cl', ''),
                        'so4': sample.get('so4', ''),
                        'k': sample.get('k', ''),
                        'ca': sample.get('ca', ''),
                        'mg': sample.get('mg', ''),
                        'na': sample.get('na', ''),
                        'cu': sample.get('cu', ''),
                        'mn': sample.get('mn', ''),
                        'fe': sample.get('fe', ''),
                        'zn': sample.get('zn', '')
                    } for sample in doc.get('samples', [])
                ]
            }
        elif collection == 'Organic Carbon & Nitrogen Worksheet':
            worksheet_data = {
                'id': str(doc.get('_id', '')),
                'title': collection,
                'lab_number': doc.get('lab_number', ''),
                'analyzed_by': doc.get('analyzed_by', {}).get('name', ''),
                'analyzed_by_date': doc.get('analyzed_by', {}).get('date', ''),
                'checked_by': doc.get('checked_by', {}).get('name', ''),
                'checked_by_date': doc.get('checked_by', {}).get('date', ''),
                'created_by': doc.get('created_by', session.get('username', 'Unknown')),
                'edited_at': doc.get('edited_at', '').strftime('%Y-%m-%d %H:%M:%S') if doc.get('edited_at') else '',
                'date': doc.get('date', doc.get('created_at', datetime.utcnow()).strftime('%Y-%m-%d')),
                'comment': doc.get('comment', ''),
                'left_table': [
                    {
                        'serial_number': row.get('serial_number', ''),
                        'lab_no': row.get('lab_no', ''),
                        'ini_vol': row.get('ini_vol', ''),
                        'titre_vol': row.get('titre_vol', ''),
                        'final_vol': row.get('final_vol', '')
                    } for row in doc.get('left_table', [])
                ],
                'right_table': [
                    {
                        'serial_number': row.get('serial_number', ''),
                        'lab_no': row.get('lab_no', ''),
                        'ini_vol': row.get('ini_vol', ''),
                        'titre_vol': row.get('titre_vol', ''),
                        'final_vol': row.get('final_vol', '')
                    } for row in doc.get('right_table', [])
                ]
            }
        elif collection == 'pH, Phosphorus, Bases & Traces Worksheet':
            worksheet_data = {
                'id': str(doc.get('_id', '')),
                'title': collection,
                'lab_number': doc.get('lab_number', ''),
                'analyzed_by': doc.get('analyzed_by', {}).get('name', ''),
                'analyzed_by_date': doc.get('analyzed_by', {}).get('date', ''),
                'checked_by': doc.get('checked_by', {}).get('name', ''),
                'checked_by_date': doc.get('checked_by', {}).get('date', ''),
                'created_by': doc.get('created_by', session.get('username', 'Unknown')),
                'edited_at': doc.get('edited_at', '').strftime('%Y-%m-%d %H:%M:%S') if doc.get('edited_at') else '',
                'date': doc.get('date_of_analysis', doc.get('created_at', datetime.utcnow()).strftime('%Y-%m-%d')),
                'comment': doc.get('comment', ''),
                'calibration_table': [
                    {
                        'serial_number': row.get('serial_number', ''),
                        'p_std_conc': row.get('p_std_conc', ''),
                        'p_abs_reading': row.get('p_abs_reading', ''),
                        'k_std_conc': row.get('k_std_conc', ''),
                        'k_abs_reading': row.get('k_abs_reading', ''),
                        'ca_std_conc': row.get('ca_std_conc', ''),
                        'ca_abs_reading': row.get('ca_abs_reading', ''),
                        'mg_std_conc': row.get('mg_std_conc', ''),
                        'mg_abs_reading': row.get('mg_abs_reading', ''),
                        'na_std_conc': row.get('na_std_conc', ''),
                        'na_abs_reading': row.get('na_abs_reading', '')
                    } for row in doc.get('calibration_table', [])
                ],
                'analysis_table': [
                    {
                        'serial_number': row.get('serial_number', ''),
                        'lab_no': row.get('lab_no', ''),
                        'ph_cacl2': row.get('ph_cacl2', ''),
                        'p_instrument_reading': row.get('p_instrument_reading', ''),
                        'p_df': row.get('p_df', ''),
                        'p_mgl': row.get('p_mgl', ''),
                        'k_instrument_reading': row.get('k_instrument_reading', ''),
                        'k_df': row.get('k_df', ''),
                        'k_mgl': row.get('k_mgl', ''),
                        'ca_instrument_reading': row.get('ca_instrument_reading', ''),
                        'ca_df': row.get('ca_df', ''),
                        'ca_mgl': row.get('ca_mgl', ''),
                        'mg_instrument_reading': row.get('mg_instrument_reading', ''),
                        'mg_df': row.get('mg_df', ''),
                        'mg_mgl': row.get('mg_mgl', ''),
                        'na_instrument_reading': row.get('na_instrument_reading', ''),
                        'na_df': row.get('na_df', ''),
                        'na_mgl': row.get('na_mgl', '')
                    } for row in doc.get('analysis_table', [])
                ]
            }
        elif collection == 'Trace Worksheet Form':
            worksheet_data = {
                'id': str(doc.get('_id', '')),
                'title': collection,
                'lab_number': doc.get('lab_number', ''),
                'analyzed_by': doc.get('analyzed_by', {}).get('name', ''),
                'analyzed_by_date': doc.get('analyzed_by', {}).get('date', ''),
                'checked_by': doc.get('checked_by', {}).get('name', ''),
                'checked_by_date': doc.get('checked_by', {}).get('date', ''),
                'created_by': doc.get('created_by', session.get('username', 'Unknown')),
                'edited_at': doc.get('edited_at', '').strftime('%Y-%m-%d %H:%M:%S') if doc.get('edited_at') else '',
                'date': doc.get('date_of_analysis', doc.get('created_at', datetime.utcnow()).strftime('%Y-%m-%d')),
                'comment': doc.get('comment', ''),
                'standards': [
                    {
                        'serial_number': standard.get('serial_number', ''),
                        'copper': standard.get('copper', {}),
                        'manganese': standard.get('manganese', {}),
                        'iron': standard.get('iron', {}),
                        'zinc': standard.get('zinc', {})
                    } for standard in doc.get('standards', [])
                ],
                'samples': [
                    {
                        'serial_number': sample.get('serial_number', ''),
                        'lab_no': sample.get('lab_no', ''),
                        'copper': sample.get('copper', {}),
                        'manganese': sample.get('manganese', {}),
                        'iron': sample.get('iron', {}),
                        'zinc': sample.get('zinc', {})
                    } for sample in doc.get('samples', [])
                ]
            }
        else:
            worksheet_data = {
                'id': str(doc.get('_id', '')),
                'title': collection,
                'lab_number': doc.get('lab_number', ''),
                'farm_location': doc.get('farm_location', ''),
                'date_received': doc.get('date_received', ''),
                'date_reported': doc.get('date_reported', ''),
                'analyzed_by': [
                    {
                        'name': analyzed.get('name', ''),
                        'signature': analyzed.get('signature', '')
                    } for analyzed in doc.get('analyzed_by', [{'name': '', 'signature': ''} for _ in range(3)])
                ],
                'checked_by': [
                    {
                        'name': checked.get('name', ''),
                        'signature': checked.get('signature', '')
                    } for checked in doc.get('checked_by', [{'name': '', 'signature': ''} for _ in range(3)])
                ],
                'created_by': doc.get('created_by', session.get('username', 'Unknown')),
                'edited_at': doc.get('edited_at', '').strftime('%Y-%m-%d %H:%M:%S') if doc.get('edited_at') else '',
                'created_at': doc.get('created_at', datetime.utcnow()).strftime('%Y-%m-%d'),
                'comment': doc.get('comment', ''),
                'samples': [
                    {
                        'field': sample.get('field', ''),
                        'sample_ref': sample.get('sample_ref', ''),
                        'soil_depth': sample.get('soil_depth', ''),
                        'lab_no': sample.get('lab_no', ''),
                        'texture': sample.get('texture', {'value': '', 'class': ''}),
                        'ph': sample.get('ph', {'value': '', 'class': ''}),
                        'conductivity': sample.get('conductivity', {'value': '', 'class': ''}),
                        'org_carbon': sample.get('org_carbon', {'value': '', 'class': ''}),
                        'nitrogen': sample.get('nitrogen', {'value': '', 'class': ''}),
                        'phosphorus_bray': sample.get('phosphorus_bray', {'value': '', 'class': ''}),
                        'phosphorus_olsen': sample.get('phosphorus_olsen', {'value': '', 'class': ''}),
                        'potassium': sample.get('potassium', {'value': '', 'class': ''}),
                        'calcium': sample.get('calcium', {'value': '', 'class': ''}),
                        'magnesium': sample.get('magnesium', {'value': '', 'class': ''}),
                        'copper': sample.get('copper', {'value': '', 'class': ''}),
                        'manganese': sample.get('manganese', {'value': '', 'class': ''}),
                        'iron': sample.get('iron', {'value': '', 'class': ''}),
                        'zinc': sample.get('zinc', {'value': '', 'class': ''})
                    } for sample in doc.get('samples', [{'field': '', 'sample_ref': '', 'soil_depth': '', 'lab_no': '', 'texture': {'value': '', 'class': ''}, 'ph': {'value': '', 'class': ''}, 'conductivity': {'value': '', 'class': ''}, 'org_carbon': {'value': '', 'class': ''}, 'nitrogen': {'value': '', 'class': ''}, 'phosphorus_bray': {'value': '', 'class': ''}, 'phosphorus_olsen': {'value': '', 'class': ''}, 'potassium': {'value': '', 'class': ''}, 'calcium': {'value': '', 'class': ''}, 'magnesium': {'value': '', 'class': ''}, 'copper': {'value': '', 'class': ''}, 'manganese': {'value': '', 'class': ''}, 'iron': {'value': '', 'class': ''}, 'zinc': {'value': '', 'class': ''}} for _ in range(5)])
                ]
            }
        return jsonify(worksheet_data)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/edit/<id>/<collection>', methods=['POST'])
def edit_worksheet(id, collection):
    try:
        collections_map = {
            'Water Analysis Worksheet': water_worksheet_collection,
            'Organic Carbon & Nitrogen Worksheet': organic_carbon_nitrogent_collection,
            'pH, Phosphorus, Bases & Traces Worksheet': ph_trace_form_collection,
            'Water Analysis Report': water_analysis_collection,
            'Trace Worksheet Form': trace_worksheet_collection,
            'Soil Analysis Report Form': soil_analysis_form_collection,
            'Equipment Operation Log Book': equipment_collection
        }
        collection_obj = collections_map.get(collection)
        if collection_obj is None:
            return jsonify({'error': 'Invalid collection'}), 400

        doc = collection_obj.find_one({'_id': ObjectId(id)})
        if doc is None:
            return jsonify({'error': 'Worksheet not found'}), 404

        if collection == 'Equipment Operation Log Book':
            update_data = {
                'equipment_name': request.form.get('equipmentname'),
                'location': request.form.get('locationname'),
                'model_no': request.form.get('modelno'),
                'serial_no': request.form.get('serialno'),
                'manufacturer': request.form.get('manufacturername'),
                'log_entries': [],
                'comment': request.form.get('comment'),
                'created_by': session.get('username', doc.get('created_by', 'Unknown')),
                'edited_at': datetime.utcnow()
            }
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
                update_data['log_entries'].append(log_entry)
                row_count += 1
        elif collection == 'Water Analysis Worksheet':
            update_data = {
                'analyzed_by': request.form.get('analyzed_by'),
                'date_checked': request.form.get('date'),
                'checked_by': request.form.get('checked_by'),
                'comment': request.form.get('comment'),
                'created_by': session.get('username', doc.get('created_by', 'Unknown')),
                'edited_at': datetime.utcnow()
            }
        elif collection == 'Organic Carbon & Nitrogen Worksheet':
            update_data = {
                'date': request.form.get('date'),
                'lab_number': request.form.get('lab_number'),
                'analyzed_by': {
                    'name': request.form.get('analyzed_by'),
                    'date': request.form.get('analyzed_by_date')
                },
                'checked_by': {
                    'name': request.form.get('checked_by'),
                    'date': request.form.get('checked_by_date')
                },
                'comment': request.form.get('comment'),
                'created_by': session.get('username', doc.get('created_by', 'Unknown')),
                'edited_at': datetime.utcnow()
            }
        elif collection == 'pH, Phosphorus, Bases & Traces Worksheet':
            update_data = {
                'lab_number': request.form.get('lab_number'),
                'date_of_analysis': request.form.get('date'),
                'analyzed_by': {
                    'name': request.form.get('analyzed_by'),
                    'date': request.form.get('analyzed_by_date')
                },
                'checked_by': {
                    'name': request.form.get('checked_by'),
                    'date': request.form.get('checked_by_date')
                },
                'comment': request.form.get('comment'),
                'created_by': session.get('username', doc.get('created_by', 'Unknown')),
                'edited_at': datetime.utcnow()
            }
        elif collection == 'Trace Worksheet Form':
            update_data = {
                'lab_number': request.form.get('lab_number'),
                'date_of_analysis': request.form.get('date_of_analysis'),
                'standards': [
                    {
                        'serial_number': i,
                        'copper': {
                            'std_conc': float(request.form.get(f'cu_std_conc{i}', 0)) if request.form.get(f'cu_std_conc{i}') else None,
                            'abs_reading': float(request.form.get(f'cu_abs_reading{i}', 0)) if request.form.get(f'cu_abs_reading{i}') else None
                        },
                        'manganese': {
                            'std_conc': float(request.form.get(f'mn_std_conc{i}', 0)) if request.form.get(f'mn_std_conc{i}') else None,
                            'abs_reading': float(request.form.get(f'mn_abs_reading{i}', 0)) if request.form.get(f'mn_abs_reading{i}') else None
                        },
                        'iron': {
                            'std_conc': float(request.form.get(f'fe_std_conc{i}', 0)) if request.form.get(f'fe_std_conc{i}') else None,
                            'abs_reading': float(request.form.get(f'fe_abs_reading{i}', 0)) if request.form.get(f'fe_abs_reading{i}') else None
                        },
                        'zinc': {
                            'std_conc': float(request.form.get(f'zn_std_conc{i}', 0)) if request.form.get(f'zn_std_conc{i}') else None,
                            'abs_reading': float(request.form.get(f'zn_abs_reading{i}', 0)) if request.form.get(f'zn_abs_reading{i}') else None
                        }
                    } for i in range(1, 6)
                ],
                'samples': [
                    {
                        'serial_number': i,
                        'lab_no': request.form.get(f'lab_no{i}'),
                        'copper': {
                            'instrument_reading': float(request.form.get(f'cu_instrument_reading{i}', 0)) if request.form.get(f'cu_instrument_reading{i}') else None,
                            'df': float(request.form.get(f'cu_df{i}', 0)) if request.form.get(f'cu_df{i}') else None,
                            'mg_l': float(request.form.get(f'cu_mg_l{i}', 0)) if request.form.get(f'cu_mg_l{i}') else None
                        },
                        'manganese': {
                            'instrument_reading': float(request.form.get(f'mn_instrument_reading{i}', 0)) if request.form.get(f'mn_instrument_reading{i}') else None,
                            'df': float(request.form.get(f'mn_df{i}', 0)) if request.form.get(f'mn_df{i}') else None,
                            'mg_l': float(request.form.get(f'mn_mg_l{i}', 0)) if request.form.get(f'mn_mg_l{i}') else None
                        },
                        'iron': {
                            'instrument_reading': float(request.form.get(f'fe_instrument_reading{i}', 0)) if request.form.get(f'fe_instrument_reading{i}') else None,
                            'df': float(request.form.get(f'fe_df{i}', 0)) if request.form.get(f'fe_df{i}') else None,
                            'mg_l': float(request.form.get(f'fe_mg_l{i}', 0)) if request.form.get(f'fe_mg_l{i}') else None
                        },
                        'zinc': {
                            'instrument_reading': float(request.form.get(f'zn_instrument_reading{i}', 0)) if request.form.get(f'zn_instrument_reading{i}') else None,
                            'df': float(request.form.get(f'zn_df{i}', 0)) if request.form.get(f'zn_df{i}') else None,
                            'mg_l': float(request.form.get(f'zn_mg_l{i}', 0)) if request.form.get(f'zn_mg_l{i}') else None
                        }
                    } for i in range(1, 31)
                ],
                'analyzed_by': {
                    'name': request.form.get('analyzedby'),
                    'date': request.form.get('dateanalyzedby')
                },
                'checked_by': {
                    'name': request.form.get('checkedby'),
                    'date': request.form.get('datechecked')
                },
                'comment': request.form.get('comment'),
                'created_by': session.get('username', doc.get('created_by', 'Unknown')),
                'edited_at': datetime.utcnow()
            }
        elif collection == 'Soil Analysis Report Form':
            update_data = {
                'lab_number': request.form.get('lab_number'),
                'farm_location': request.form.get('farm_location'),
                'date_received': request.form.get('date_received'),
                'date_reported': request.form.get('date_reported'),
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
                'comment': request.form.get('comment'),
                'created_by': session.get('username', doc.get('created_by', 'Unknown')),
                'edited_at': datetime.utcnow()
            }
        else:
            update_data = {
                'analyzed_by': {
                    'name': request.form.get('analyzed_by'),
                    'date': request.form.get('analyzed_by_date')
                },
                'checked_by': {
                    'name': request.form.get('checked_by'),
                    'date': request.form.get('checked_by_date')
                },
                'comment': request.form.get('comment'),
                'date': request.form.get('date') or request.form.get('date_of_analysis'),
                'created_by': session.get('username', doc.get('created_by', 'Unknown')),
                'edited_at': datetime.utcnow()
            }
            if collection in ['pH, Phosphorus, Bases & Traces Worksheet', 'Trace Worksheet Form'] and 'date' in update_data:
                update_data['date_of_analysis'] = update_data.pop('date')

        update_data = {k: v for k, v in update_data.items() if v is not None}
        collection_obj.update_one({'_id': ObjectId(id)}, {'$set': update_data})

        updated_doc = collection_obj.find_one({'_id': ObjectId(id)})
        updated_worksheet = {
            'id': str(updated_doc.get('_id', '')),
            'title': collection,
            'created_by': updated_doc.get('created_by', session.get('username', 'Unknown')),
            'date': updated_doc.get('date_of_analysis' if collection in ['pH, Phosphorus, Bases & Traces Worksheet', 'Trace Worksheet Form'] else 'date_checked' if collection == 'Water Analysis Worksheet' else 'date', updated_doc.get('created_at', datetime.utcnow()).strftime('%Y-%m-%d')),
            'comment': updated_doc.get('comment', ''),
            'collection': collection,
            'edited_at': updated_doc.get('edited_at', '').strftime('%Y-%m-%d %H:%M:%S') if updated_doc.get('edited_at') else ''
        }
        flash('Worksheet updated successfully!', 'success')
        return redirect(url_for('submit.submit'))
    except Exception as e:
        flash(f'Error updating worksheet: {str(e)}', 'danger')
        return redirect(url_for('submit.submit'))
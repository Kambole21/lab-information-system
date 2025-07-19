from flask import Flask, Blueprint, redirect, render_template, url_for, request, flash, Response, session
from app import trace_worksheet_collection
from datetime import datetime
from bson import ObjectId
import csv
from io import StringIO
import subprocess
import os
import tempfile
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

bp = Blueprint('trace', __name__)

@bp.route('/trace', methods=['GET', 'POST'])
def trace():
    role = session.get('role', 'normal')
    if request.method == 'POST':
        try:
            # Collect form data
            form_data = {
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
                'created_at': datetime.utcnow(),
                'created_by': session.get('username', 'Unknown')
            }

            # Basic validation
            if not form_data['lab_number'] or not form_data['date_of_analysis']:
                flash('Please fill in all required metadata fields (Lab # and Date of Analysis).', 'danger')
                return redirect(url_for('trace.trace'))

            # Ensure at least one sample has data
            has_sample_data = False
            for sample in form_data['samples']:
                if sample['lab_no'] or any(
                    value is not None for key, value in sample['copper'].items()
                ) or any(
                    value is not None for key, value in sample['manganese'].items()
                ) or any(
                    value is not None for key, value in sample['iron'].items()
                ) or any(
                    value is not None for key, value in sample['zinc'].items()
                ):
                    has_sample_data = True
                    break
            if not has_sample_data:
                flash('Please provide data for at least one sample.', 'danger')
                return redirect(url_for('trace.trace'))

            # Handle edit case
            if 'id' in request.form:
                form_data['edited_at'] = datetime.utcnow()
                trace_worksheet_collection.update_one(
                    {'_id': ObjectId(request.form['id'])},
                    {'$set': form_data}
                )
                flash('Trace elements worksheet updated successfully!', 'success')
            else:
                # Insert into MongoDB
                result = trace_worksheet_collection.insert_one(form_data)
                if result.inserted_id:
                    flash('Trace elements worksheet submitted successfully!', 'success')
                else:
                    flash('Failed to submit the worksheet. Please try again.', 'danger')

            return redirect(url_for('submit.submit'))

        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'danger')
            return redirect(url_for('trace.trace'))

    # Handle GET request for editing
    worksheet = {}
    if 'id' in request.args:
        try:
            worksheet = trace_worksheet_collection.find_one({'_id': ObjectId(request.args['id'])})
            if not worksheet:
                flash('Trace worksheet not found.', 'danger')
                return redirect(url_for('submit.submit'))
        except Exception as e:
            flash(f'Error fetching trace worksheet: {str(e)}', 'danger')
            return redirect(url_for('submit.submit'))

    return render_template('trace_worksheet.html', worksheet=worksheet, role = role)

@bp.route('/view_trace_worksheet/<id>')
def view_trace_worksheet(id):
    role = session.get('role', 'normal')
    try:
        worksheet = trace_worksheet_collection.find_one({'_id': ObjectId(id)})
        if not worksheet:
            flash('Trace worksheet not found.', 'danger')
            return redirect(url_for('submit.submit'))
        return render_template('view_trace_worksheet.html', worksheet=worksheet, role = role)
    except Exception as e:
        flash(f'Error fetching trace worksheet: {str(e)}', 'danger')
        return redirect(url_for('submit.submit'))

@bp.route('/download_csv/<id>')
def download_csv(id):
    try:
        worksheet = trace_worksheet_collection.find_one({'_id': ObjectId(id)})
        if not worksheet:
            flash('Trace worksheet not found.', 'danger')
            return redirect(url_for('submit.submit'))

        output = StringIO()
        writer = csv.writer(output)

        # Write metadata
        writer.writerow(['Lab Number', worksheet.get('lab_number', '')])
        writer.writerow(['Date of Analysis', worksheet.get('date_of_analysis', '')])
        writer.writerow(['Analyzed By', worksheet.get('analyzed_by', {}).get('name', '')])
        writer.writerow(['Analyzed By Date', worksheet.get('analyzed_by', {}).get('date', '')])
        writer.writerow(['Checked By', worksheet.get('checked_by', {}).get('name', '')])
        writer.writerow(['Checked By Date', worksheet.get('checked_by', {}).get('date', '')])
        writer.writerow([])  # Empty row for separation

        # Write standards
        writer.writerow(['Standards'])
        writer.writerow(['S/N', 'Cu Std Conc', 'Cu Abs Reading', 'Mn Std Conc', 'Mn Abs Reading', 
                         'Fe Std Conc', 'Fe Abs Reading', 'Zn Std Conc', 'Zn Abs Reading'])
        for standard in worksheet.get('standards', []):
            writer.writerow([
                standard.get('serial_number', ''),
                standard.get('copper', {}).get('std_conc', ''),
                standard.get('copper', {}).get('abs_reading', ''),
                standard.get('manganese', {}).get('std_conc', ''),
                standard.get('manganese', {}).get('abs_reading', ''),
                standard.get('iron', {}).get('std_conc', ''),
                standard.get('iron', {}).get('abs_reading', ''),
                standard.get('zinc', {}).get('std_conc', ''),
                standard.get('zinc', {}).get('abs_reading', '')
            ])
        writer.writerow([])  # Empty row for separation

        # Write samples
        writer.writerow(['Samples'])
        writer.writerow(['S/N', 'Lab No.', 
                         'Cu Instrument Reading', 'Cu D.F', 'Cu mg/l',
                         'Mn Instrument Reading', 'Mn D.F', 'Mn mg/l',
                         'Fe Instrument Reading', 'Fe D.F', 'Fe mg/l',
                         'Zn Instrument Reading', 'Zn D.F', 'Zn mg/l'])
        for sample in worksheet.get('samples', []):
            if sample.get('lab_no') or any(
                value is not None for key, value in sample.get('copper', {}).items()
            ) or any(
                value is not None for key, value in sample.get('manganese', {}).items()
            ) or any(
                value is not None for key, value in sample.get('iron', {}).items()
            ) or any(
                value is not None for key, value in sample.get('zinc', {}).items()
            ):
                writer.writerow([
                    sample.get('serial_number', ''),
                    sample.get('lab_no', ''),
                    sample.get('copper', {}).get('instrument_reading', ''),
                    sample.get('copper', {}).get('df', ''),
                    sample.get('copper', {}).get('mg_l', ''),
                    sample.get('manganese', {}).get('instrument_reading', ''),
                    sample.get('manganese', {}).get('df', ''),
                    sample.get('manganese', {}).get('mg_l', ''),
                    sample.get('iron', {}).get('instrument_reading', ''),
                    sample.get('iron', {}).get('df', ''),
                    sample.get('iron', {}).get('mg_l', ''),
                    sample.get('zinc', {}).get('instrument_reading', ''),
                    sample.get('zinc', {}).get('df', ''),
                    sample.get('zinc', {}).get('mg_l', '')
                ])

        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment;filename=trace_worksheet_{id}.csv'}
        )
    except Exception as e:
        flash(f'Error generating CSV: {str(e)}', 'danger')
        return redirect(url_for('submit.submit'))

@bp.route('/download_pdf/<id>')
def download_pdf(id):
    try:
        worksheet = trace_worksheet_collection.find_one({'_id': ObjectId(id)})
        if not worksheet:
            flash('Trace worksheet not found.', 'danger')
            return redirect(url_for('submit.submit'))

        # Defining LaTeX template
        latex_template = r"""
        \documentclass[a4paper,12pt]{article}
        \usepackage{geometry}
        \usepackage{booktabs}
        \usepackage{longtable}
        \usepackage{pdflscape}
        \usepackage{siunitx}
        \sisetup{detect-all}
        \usepackage{noto}

        \geometry{margin=1in}
        \title{Trace Worksheet}
        \author{}
        \date{}

        \begin{document}

        % Setting up document title and metadata
        \maketitle
        \section*{Trace Worksheet}
        \begin{tabular}{ll}
            \textbf{Lab Number:} & {lab_number} \\
            \textbf{Date of Analysis:} & {date_of_analysis} \\
            \textbf{Analyzed By:} & {analyzed_by_name} \\
            \textbf{Analyzed By Date:} & {analyzed_by_date} \\
            \textbf{Checked By:} & {checked_by_name} \\
            \textbf{Checked By Date:} & {checked_by_date} \\
            \textbf{Comment:} & {comment} \\
        \end{tabular}

        % Standards table
        \section*{Standards}
        \begin{longtable}{c S[table-format=2.0] S[table-format=3.2] S[table-format=2.0] S[table-format=3.2] S[table-format=2.0] S[table-format=3.2] S[table-format=2.0] S[table-format=3.2]}
            \toprule
            \textbf{S/N} & \textbf{Cu Std Conc} & \textbf{Cu Abs Reading} & \textbf{Mn Std Conc} & \textbf{Mn Abs Reading} & \textbf{Fe Std Conc} & \textbf{Fe Abs Reading} & \textbf{Zn Std Conc} & \textbf{Zn Abs Reading} \\
            \midrule
            \endhead
            {standards_rows}
            \bottomrule
        \end{longtable}

        % Samples table
        \section*{Samples}
        \begin{landscape}
        \begin{longtable}{c l S[table-format=3.2] S[table-format=3.2] S[table-format=3.2] S[table-format=3.2] S[table-format=3.2] S[table-format=3.2] S[table-format=3.2] S[table-format=3.2] S[table-format=3.2] S[table-format=3.2] S[table-format=3.2] S[table-format=3.2]}
            \toprule
            \textbf{S/N} & \textbf{Lab No.} & \textbf{Cu Instrument Reading} & \textbf{Cu D.F} & \textbf{Cu mg/l} & \textbf{Mn Instrument Reading} & \textbf{Mn D.F} & \textbf{Mn mg/l} & \textbf{Fe Instrument Reading} & \textbf{Fe D.F} & \textbf{Fe mg/l} & \textbf{Zn Instrument Reading} & \textbf{Zn D.F} & \textbf{Zn mg/l} \\
            \midrule
            \endhead
            {samples_rows}
            \bottomrule
        \end{longtable}
        \end{landscape}

        \end{document}
        """

        # Preparing standards table rows
        standards_rows = []
        for standard in worksheet.get('standards', []):
            row = (
                f"{standard.get('serial_number', '')} & "
                f"{standard.get('copper', {}).get('std_conc', '')} & "
                f"{standard.get('copper', {}).get('abs_reading', '')} & "
                f"{standard.get('manganese', {}).get('std_conc', '')} & "
                f"{standard.get('manganese', {}).get('abs_reading', '')} & "
                f"{standard.get('iron', {}).get('std_conc', '')} & "
                f"{standard.get('iron', {}).get('abs_reading', '')} & "
                f"{standard.get('zinc', {}).get('std_conc', '')} & "
                f"{standard.get('zinc', {}).get('abs_reading', '')} \\\\"
            )
            standards_rows.append(row)

        # Preparing samples table rows
        samples_rows = []
        for sample in worksheet.get('samples', []):
            if sample.get('lab_no') or any(
                value is not None for key, value in sample.get('copper', {}).items()
            ) or any(
                value is not None for key, value in sample.get('manganese', {}).items()
            ) or any(
                value is not None for key, value in sample.get('iron', {}).items()
            ) or any(
                value is not None for key, value in sample.get('zinc', {}).items()
            ):
                row = (
                    f"{sample.get('serial_number', '')} & "
                    f"{sample.get('lab_no', '')} & "
                    f"{sample.get('copper', {}).get('instrument_reading', '')} & "
                    f"{sample.get('copper', {}).get('df', '')} & "
                    f"{sample.get('copper', {}).get('mg_l', '')} & "
                    f"{sample.get('manganese', {}).get('instrument_reading', '')} & "
                    f"{sample.get('manganese', {}).get('df', '')} & "
                    f"{sample.get('manganese', {}).get('mg_l', '')} & "
                    f"{sample.get('iron', {}).get('instrument_reading', '')} & "
                    f"{sample.get('iron', {}).get('df', '')} & "
                    f"{sample.get('iron', {}).get('mg_l', '')} & "
                    f"{sample.get('zinc', {}).get('instrument_reading', '')} & "
                    f"{sample.get('zinc', {}).get('df', '')} & "
                    f"{sample.get('zinc', {}).get('mg_l', '')} \\\\"
                )
                samples_rows.append(row)

        # Escaping special characters for LaTeX
        def escape_latex(text):
            if not isinstance(text, str):
                text = str(text)
            replacements = {
                '&': r'\&',
                '%': r'\%',
                '$': r'\$',
                '#': r'\#',
                '_': r'\_',
                '{': r'\{',
                '}': r'\}',
                '~': r'\textasciitilde{}',
                '^': r'\textasciicircum{}',
                '\\': r'\textbackslash{}'
            }
            for old, new in replacements.items():
                text = text.replace(old, new)
            return text

        # Formatting metadata for LaTeX
        lab_number = escape_latex(worksheet.get('lab_number', ''))
        date_of_analysis = escape_latex(worksheet.get('date_of_analysis', ''))
        analyzed_by_name = escape_latex(worksheet.get('analyzed_by', {}).get('name', ''))
        analyzed_by_date = escape_latex(worksheet.get('analyzed_by', {}).get('date', ''))
        checked_by_name = escape_latex(worksheet.get('checked_by', {}).get('name', ''))
        checked_by_date = escape_latex(worksheet.get('checked_by', {}).get('date', ''))
        comment = escape_latex(worksheet.get('comment', ''))

        # Creating LaTeX content
        latex_content = latex_template.format(
            lab_number=lab_number,
            date_of_analysis=date_of_analysis,
            analyzed_by_name=analyzed_by_name,
            analyzed_by_date=analyzed_by_date,
            checked_by_name=checked_by_name,
            checked_by_date=checked_by_date,
            comment=comment,
            standards_rows='\n'.join(standards_rows),
            samples_rows='\n'.join(samples_rows)
        )

        # Creating temporary directory for LaTeX processing
        with tempfile.TemporaryDirectory() as tmpdirname:
            tex_file_path = os.path.join(tmpdirname, f'trace_worksheet_{id}.tex')
            pdf_file_path = os.path.join(tmpdirname, f'trace_worksheet_{id}.pdf')

            # Writing LaTeX file
            with open(tex_file_path, 'w', encoding='utf-8') as tex_file:
                tex_file.write(latex_content)

            # Running latexmk to compile LaTeX to PDF
            try:
                result = subprocess.run(
                    ['latexmk', '-pdf', '-pdflatex=pdflatex', tex_file_path],
                    cwd=tmpdirname,
                    capture_output=True,
                    text=True,
                    check=True
                )
                logger.debug(f"latexmk output: {result.stdout}")
            except subprocess.CalledProcessError as e:
                logger.error(f"latexmk error: {e.stderr}")
                flash(f'Error generating PDF: {e.stderr}', 'danger')
                return redirect(url_for('submit.submit'))

            # Reading the generated PDF
            try:
                with open(pdf_file_path, 'rb') as pdf_file:
                    pdf_data = pdf_file.read()
            except FileNotFoundError:
                flash('PDF file could not be generated.', 'danger')
                return redirect(url_for('submit.submit'))

            # Cleaning up LaTeX auxiliary files
            try:
                subprocess.run(['latexmk', '-c'], cwd=tmpdirname, capture_output=True)
            except subprocess.CalledProcessError as e:
                logger.warning(f"Error cleaning up LaTeX files: {e.stderr}")

        # Serving the PDF
        return Response(
            pdf_data,
            mimetype='application/pdf',
            headers={'Content-Disposition': f'attachment;filename=trace_worksheet_{id}.pdf'}
        )

    except Exception as e:
        logger.error(f"Error generating PDF: {str(e)}")
        flash(f'Error generating PDF: {str(e)}', 'danger')
        return redirect(url_for('submit.submit'))
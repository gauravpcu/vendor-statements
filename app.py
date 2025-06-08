from flask import Flask, render_template, request, jsonify, send_from_directory, send_file, current_app
import os
import io
import magic
import logging
import json
import datetime
import pandas as pd
from file_parser import extract_headers, extract_data, extract_headers_from_pdf_tables
from azure_openai_client import test_azure_openai_connection, azure_openai_configured
from header_mapper import generate_mappings
from chatbot_service import get_mapping_suggestions
from data_validator import validate_uniqueness, validate_invoice_via_api # Import new validation functions
# from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB limit
TEMPLATES_DIR = "templates_storage"
LEARNED_PREFERENCES_DIR = "learned_preferences_storage"

# Load external API configs
app.config['INVOICE_VALIDATION_API_URL'] = os.getenv('INVOICE_VALIDATION_API_URL')
app.config['INVOICE_VALIDATION_API_KEY'] = os.getenv('INVOICE_VALIDATION_API_KEY')


# --- Field Definitions ---
FIELD_DEFINITIONS = {}

def load_field_definitions():
    global FIELD_DEFINITIONS
    try:
        with open('field_definitions.json', 'r', encoding='utf-8') as f:
            FIELD_DEFINITIONS = json.load(f)
    except FileNotFoundError:
        logging.error("CRITICAL: field_definitions.json not found. Field mapping will not work.")
        FIELD_DEFINITIONS = {}
    except json.JSONDecodeError:
        logging.error("CRITICAL: field_definitions.json is not valid JSON. Field mapping will not work.")
        FIELD_DEFINITIONS = {}
    except Exception as e:
        logging.error(f"CRITICAL: An unexpected error occurred loading field_definitions.json: {e}")
        FIELD_DEFINITIONS = {}


# --- Logger Setup ---
logger = logging.getLogger('upload_history')
logger.setLevel(logging.INFO)
file_handler_configured = False
if logger.handlers:
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler) and handler.baseFilename.endswith('upload_history.log'):
            file_handler_configured = True
            break

if not file_handler_configured:
    fh = logging.FileHandler('upload_history.log')
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
# --- End Logger Setup ---

# Create directories if they don't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(LEARNED_PREFERENCES_DIR, exist_ok=True)

load_field_definitions()

try:
    logger.info("Attempting to test Azure OpenAI connection...")
    test_result = test_azure_openai_connection()
    logger.info(f"Azure OpenAI Connection Test Result: {test_result}")
    if not test_result.get("success"):
        logger.warning(f"Azure OpenAI connection test failed: {test_result.get('message')} - Details: {test_result.get('details')}")
    if not azure_openai_configured:
        logger.warning("Azure OpenAI client is not configured due to missing environment variables or initialization failure.")
except Exception as e:
    logger.error(f"An unexpected error occurred during the Azure OpenAI connection test call: {e}", exc_info=True)

# Log warning for external Invoice Validation API if URL is not set
if not app.config['INVOICE_VALIDATION_API_URL']:
    logger.warning("INVOICE_VALIDATION_API_URL is not set in environment variables. External invoice validation will be disabled.")

TEMP_PDF_DATA_FOR_EXTRACTION = {}

SUPPORTED_MIME_TYPES = {
    'application/pdf': 'PDF',
    'application/vnd.ms-excel': 'XLS',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'XLSX',
    'text/csv': 'CSV'
}

@app.route('/')
def index():
    return render_template('index.html', field_definitions_json=json.dumps(FIELD_DEFINITIONS))

@app.route('/manage_templates')
def manage_templates_page():
    return render_template('manage_templates.html')

@app.route('/manage_preferences')
def manage_preferences_page():
    return render_template('manage_preferences.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    files = request.files.getlist('files[]')
    results = []
    uploaded_file_count = 0

    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    if len(files) > 10:
        for file_storage in files:
            results.append({
                "filename": file_storage.filename if file_storage else "Unknown",
                "success": False, "message": "Too many files uploaded (limit is 10).", "file_type": "N/A"
            })
        return jsonify(results), 400

    if not any(file_storage and file_storage.filename for file_storage in files):
        return jsonify([{"filename": "N/A", "success": False, "message": "No files selected.", "file_type": "N/A"}]), 400

    for file_storage in files:
        if file_storage and file_storage.filename:
            filename = file_storage.filename
            results_entry = {
                "filename": filename, "success": False, "message": "File processing started.",
                "file_type": "unknown", "headers": [], "field_mappings": []
            }
            try:
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file_storage.save(file_path)

                try:
                    mime_type = magic.from_file(file_path, mime=True)
                    detected_type_name = SUPPORTED_MIME_TYPES.get(mime_type)
                    if detected_type_name:
                        results_entry["file_type"] = detected_type_name
                        results_entry["success"] = True
                        results_entry["message"] = "Upload and type detection successful."
                        uploaded_file_count += 1
                    else:
                        results_entry["message"] = f"Unsupported file type: {mime_type}."
                        results_entry["file_type"] = mime_type
                        results_entry["success"] = False
                except magic.MagicException:
                    results_entry["message"] = "Error detecting file type (file may be corrupted)."
                    results_entry["file_type"] = "error_detection"
                    results_entry["success"] = False
                except Exception as e_detect:
                    results_entry["message"] = f"Error during file type detection: {str(e_detect)}"
                    results_entry["file_type"] = "error_detection_general"
                    results_entry["success"] = False

                if results_entry["success"] and results_entry["file_type"] in ["CSV", "XLSX", "XLS", "PDF"]:
                    headers_extraction_result = extract_headers(file_path, results_entry["file_type"])

                    if isinstance(headers_extraction_result, list):
                        results_entry["headers"] = headers_extraction_result
                        if headers_extraction_result:
                            mappings = generate_mappings(headers_extraction_result, FIELD_DEFINITIONS)
                            results_entry["field_mappings"] = mappings
                            logger.info(f"Generated {len(mappings)} field mappings for {filename} (Type: {results_entry['file_type']}).")
                            results_entry["message"] = "Headers extracted and auto-mapped."
                        else:
                            results_entry["message"] += " No headers were found/extracted."
                    elif isinstance(headers_extraction_result, dict) and "error" in headers_extraction_result:
                        results_entry["success"] = False
                        results_entry["message"] = headers_extraction_result["error"]

                    # If PDF and headers were extracted successfully, cache data_rows for later use in /process_file_data
                    if results_entry["file_type"] == "PDF" and results_entry["success"] and isinstance(headers_extraction_result, list):
                        # Call extract_headers_from_pdf_tables again to get the full context including data_rows
                        # This is less ideal than extract_headers returning everything, but avoids major refactor of extract_headers now.
                        logger.info(f"Fetching full PDF context (headers and data_rows) for {filename} for caching.")
                        pdf_full_extraction_info = extract_headers_from_pdf_tables(file_path)
                        if isinstance(pdf_full_extraction_info, dict) and not pdf_full_extraction_info.get("error"):
                            original_pdf_headers = pdf_full_extraction_info.get('headers')
                            pdf_table_data_rows = pdf_full_extraction_info.get('data_rows')
                            if original_pdf_headers is not None and pdf_table_data_rows is not None:
                                TEMP_PDF_DATA_FOR_EXTRACTION[filename] = {
                                    'headers': original_pdf_headers,
                                    'data_rows': pdf_table_data_rows
                                }
                                logger.info(f"Cached 'data_rows' for PDF {filename}. Headers count: {len(original_pdf_headers)}, Data rows count: {len(pdf_table_data_rows)}")
                            else:
                                logger.warning(f"Could not cache data_rows for PDF {filename} as headers or data_rows were missing from pdf_full_extraction_info.")
                        else:
                            logger.warning(f"Failed to get full PDF context for caching data_rows for {filename}. Error: {pdf_full_extraction_info.get('error') if isinstance(pdf_full_extraction_info, dict) else 'Unknown error'}")

                results.append(results_entry)

            except Exception as e_save:
                results_entry = {"filename": filename, "success": False, "message": f"Error saving or processing file: {str(e_save)}", "file_type": "error_system", "headers": [], "field_mappings": []}
                results.append(results_entry)

            log_message = (f"File: {filename}, Status: {'Success' if results_entry.get('success') else 'Failure'}, Type: {results_entry.get('file_type', 'unknown')}, "
                           f"Message: {results_entry.get('message')}, Headers: {len(results_entry.get('headers',[]))}, Mappings: {len(results_entry.get('field_mappings',[]))}")
            logger.info(log_message)

    return jsonify(results)

@app.route('/chatbot_suggest_mapping', methods=['POST'])
def chatbot_suggest_mapping_route():
    data = request.get_json()
    if not data: return jsonify({"error": "No data provided"}), 400
    original_header = data.get('original_header')
    current_mapped_field = data.get('current_mapped_field')
    if not original_header: return jsonify({"error": "Missing 'original_header'"}), 400
    logger.info(f"Chatbot suggestion for: '{original_header}', current: '{current_mapped_field}'")
    try:
        suggestions = get_mapping_suggestions(original_header, current_mapped_field, FIELD_DEFINITIONS)
        return jsonify(suggestions)
    except Exception as e:
        logger.error(f"Chatbot suggestion error: {e}", exc_info=True)
        return jsonify({"error": "Internal error generating suggestions."}), 500


@app.route('/process_file_data', methods=['POST'])
def process_file_data_route():
    data = request.get_json()
    if not data: return jsonify({"error": "No data provided"}), 400
    file_identifier = data.get('file_identifier')
    finalized_mappings = data.get('finalized_mappings')
    file_type = data.get('file_type')
    try:
        skip_rows = int(data.get('skip_rows', 0))
        if skip_rows < 0: skip_rows = 0
    except ValueError:
        logger.warning(f"Invalid skip_rows value received in /process_file_data: {data.get('skip_rows')}. Defaulting to 0.")
        skip_rows = 0

    if not all([file_identifier, finalized_mappings, file_type]): # skip_rows is optional, defaults to 0
        return jsonify({"error": "Missing required fields (file_identifier, finalized_mappings, file_type)"}), 400

    file_path_on_disk = os.path.join(app.config['UPLOAD_FOLDER'], file_identifier)
    if not os.path.exists(file_path_on_disk):
        if not os.path.exists(file_identifier):
            logger.error(f"File not found: {file_identifier}")
            return jsonify({"error": f"File not found: {file_identifier}"}), 404
        file_path_on_disk = file_identifier

    logger.info(f"Processing data for: {file_path_on_disk}, type: {file_type}")
    try:
        if file_type == "PDF":
            raw_pdf_content_for_extraction = TEMP_PDF_DATA_FOR_EXTRACTION.pop(file_identifier, None)
            if raw_pdf_content_for_extraction is None:
                logger.error(f"PDF data for {file_identifier} not found in TEMP_PDF_DATA_FOR_EXTRACTION cache. It might have been processed already or upload failed to cache it.")
                # Attempt to re-fetch PDF context as a fallback, though ideally it should be cached
                logger.info(f"Attempting to re-fetch PDF context for {file_identifier} as it was not in cache.")
                pdf_context_fallback = extract_headers_from_pdf_tables(file_path_on_disk)
                if isinstance(pdf_context_fallback, dict) and not pdf_context_fallback.get("error"):
                    raw_pdf_content_for_extraction = {
                        'headers': pdf_context_fallback.get('headers'),
                        'data_rows': pdf_context_fallback.get('data_rows')
                    }
                    logger.info(f"Successfully re-fetched PDF context for {file_identifier} for data extraction.")
                else:
                    error_msg = f"PDF data for {file_identifier} not found in cache and could not be re-fetched. Please re-upload the file or check earlier logs. Fallback error: {pdf_context_fallback.get('error', 'Unknown error during fallback') if isinstance(pdf_context_fallback, dict) else 'Type error in fallback result'}."
                    logger.error(error_msg)
                    return jsonify({"error": error_msg}), 400 # 400 or 500 depending on whether client can fix

            # For PDF, skip_rows is not directly passed to extract_data as the raw_pdf_content already reflects the chosen table.
            # skip_rows from client might be relevant if we were to re-select a table, but current logic doesn't do that here.
            extracted_data_list_or_error = extract_data(
                file_path_on_disk,
                file_type,
                finalized_mappings,
                raw_pdf_table_content=raw_pdf_content_for_extraction
                # skip_rows is NOT passed here for PDF with raw_pdf_table_content
            )
        else: # For CSV/Excel
            extracted_data_list_or_error = extract_data(
                file_path_on_disk,
                file_type,
                finalized_mappings,
                skip_rows=skip_rows # skip_rows is relevant for CSV/Excel
            )

        if isinstance(extracted_data_list_or_error, dict) and "error" in extracted_data_list_or_error:
            logger.error(f"Data extraction error for {file_path_on_disk}: {extracted_data_list_or_error['error']}")
            return jsonify(extracted_data_list_or_error), 400

        return jsonify({'data': extracted_data_list_or_error, 'message': f'Successfully processed {len(extracted_data_list_or_error)} records.' if isinstance(extracted_data_list_or_error, list) else 'Processed data.'})
    except Exception as e:
        logger.error(f"File processing error for {file_path_on_disk}: {e}", exc_info=True)
        return jsonify({"error": "Internal error processing file."}), 500

@app.route('/view_uploaded_file/<path:filename>')
def view_uploaded_file(filename):
    try:
        upload_folder_abs = os.path.abspath(app.config['UPLOAD_FOLDER'])
        logger.info(f"Serving file: {filename} from {upload_folder_abs}")
        return send_from_directory(upload_folder_abs, filename, as_attachment=False)
    except FileNotFoundError:
        logger.error(f"File not found: {filename} in {upload_folder_abs}", exc_info=True)
        return "File not found.", 404
    except Exception as e:
        logger.error(f"Error serving file {filename}: {e}", exc_info=True)
        return "Error serving file.", 500

@app.route('/save_template', methods=['POST'])
def save_template_route():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    original_template_name = data.get('template_name', '').strip()
    field_mappings = data.get('field_mappings')
    overwrite = data.get('overwrite', False)

    if not original_template_name:
        return jsonify({"error": "Template name is required."}), 400

    if not field_mappings or not isinstance(field_mappings, list) or len(field_mappings) == 0:
        return jsonify({"error": "Field mappings are required and cannot be empty."}), 400

    sanitized_name_part = "".join(c if c.isalnum() or c in ('_', '-') else '' for c in original_template_name)
    if not sanitized_name_part:
        logger.warning(f"Template name '{original_template_name}' sanitized to empty. Not saving.")
        return jsonify({"error": "Invalid template name after sanitization. Please provide a more descriptive name."}), 400

    safe_target_filename = f"{sanitized_name_part}.json"
    target_file_path = os.path.join(TEMPLATES_DIR, safe_target_filename)

    # Check 1: Exact Original Name Match in a *Different* File
    # This check should ideally happen regardless of the overwrite flag for the current target file,
    # as it's about the *display name* being unique across all templates.
    if os.path.exists(TEMPLATES_DIR):
        for existing_s_filename in os.listdir(TEMPLATES_DIR):
            if not existing_s_filename.endswith(".json") or existing_s_filename == safe_target_filename:
                continue
            try:
                with open(os.path.join(TEMPLATES_DIR, existing_s_filename), 'r', encoding='utf-8') as f:
                    existing_template_data = json.load(f)
                if existing_template_data.get('template_name') == original_template_name:
                    return jsonify({
                        'status': 'error', 'error_type': 'NAME_ALREADY_EXISTS_IN_OTHER_FILE',
                        'message': f"A template with the name '{original_template_name}' already exists (saved as '{existing_s_filename}'). Please choose a unique name.",
                        'conflicting_filename': existing_s_filename
                    }), 409
            except (IOError, json.JSONDecodeError) as e:
                logger.error(f"Error reading/parsing {existing_s_filename} during name conflict check: {e}")

    filename_exists = os.path.exists(target_file_path)

    if filename_exists and not overwrite:
        existing_internal_name = "N/A"
        try:
            with open(target_file_path, 'r', encoding='utf-8') as f:
                loaded_content = json.load(f)
            existing_internal_name = loaded_content.get('template_name', 'N/A')
        except (IOError, json.JSONDecodeError):
            logger.error(f"Could not read existing template {target_file_path} to get its name during conflict check.")

        return jsonify({
            'status': 'conflict', 'error_type': 'FILENAME_CLASH',
            'message': f"A template file that would be named '{safe_target_filename}' already exists (it currently stores a template named '{existing_internal_name}'). Do you want to overwrite it?",
            'filename': safe_target_filename, 'existing_template_name': existing_internal_name
        }), 409

    if (filename_exists and overwrite) or (not filename_exists and overwrite):
        skip_rows = data.get('skip_rows', 0)
        try: # Ensure skip_rows is a non-negative integer
            skip_rows = int(skip_rows)
            if skip_rows < 0: skip_rows = 0
        except (ValueError, TypeError):
            skip_rows = 0
            logger.warning(f"Invalid skip_rows value received for template '{original_template_name}', defaulting to 0.")

        template_data = {
            "template_name": original_template_name,
            "filename": safe_target_filename,
            "creation_timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "field_mappings": field_mappings,
            "skip_rows": skip_rows # Add skip_rows to the template data
        }
        try:
            with open(target_file_path, 'w', encoding='utf-8') as f:
                json.dump(template_data, f, indent=4)

            status_code = 200 if filename_exists else 201
            action_message = "overwritten" if filename_exists else "saved"
            logger.info(f"Template '{original_template_name}' {action_message} as '{safe_target_filename}'.")
            return jsonify({
                "status": "success",
                "message": f"Template '{original_template_name}' {action_message} successfully.", # Distinct message
                "template_name": original_template_name, "filename": safe_target_filename
            }), status_code
        except IOError as e:
            logger.error(f"IOError saving/overwriting template '{safe_target_filename}': {e}", exc_info=True)
            return jsonify({"error": f"Could not save template file: {str(e)}"}), 500
        except Exception as e:
            logger.error(f"Unexpected error saving/overwriting template '{safe_target_filename}': {e}", exc_info=True)
            return jsonify({"error": "An unexpected server error occurred while saving."}), 500

    elif not filename_exists and not overwrite:
        return jsonify({
            'status': 'no_conflict_proceed_to_save',
            'message': 'No conflict found. Template name and filename are available.',
            'filename': safe_target_filename, 'template_name': original_template_name
        }), 200

    logger.error(f"Reached unexpected state in /save_template for {original_template_name} / {safe_target_filename} with overwrite={overwrite}")
    return jsonify({"error": "Unexpected state in save template logic."}), 500


@app.route('/list_templates', methods=['GET'])
def list_templates_route():
    # ... (implementation as before)
    templates_info = []
    if not os.path.exists(TEMPLATES_DIR):
        logger.warning(f"Templates dir '{TEMPLATES_DIR}' not found.")
        return jsonify({'templates': [], 'message': 'Templates directory not found.'})
    try:
        for f_name in os.listdir(TEMPLATES_DIR):
            if f_name.endswith(".json"):
                template_file_path = os.path.join(TEMPLATES_DIR, f_name)
                try:
                    with open(template_file_path, 'r', encoding='utf-8') as f:
                        template_data = json.load(f)
                        display_name = template_data.get('template_name')
                        file_id = template_data.get('filename', f_name) # Use actual filename as file_id for robustness
                        creation_timestamp = template_data.get('creation_timestamp', 'N/A')

                        if display_name and file_id:
                            templates_info.append({
                                'display_name': display_name,
                                'file_id': file_id, # This is the actual filename like "MyTemplate.json"
                                'creation_timestamp': creation_timestamp
                            })
                        else:
                            logger.warning(f"Skipping template '{f_name}': missing 'template_name' or 'filename' key in JSON content.")
                except Exception as e_file:
                    logger.error(f"Error processing template file '{f_name}': {e_file}", exc_info=True)
        templates_info.sort(key=lambda x: x['display_name'].lower())
        return jsonify({'templates': templates_info})
    except Exception as e_list:
        logger.error(f"Error listing templates from '{TEMPLATES_DIR}': {e_list}", exc_info=True)
        return jsonify({'templates': [], 'error': 'Could not retrieve templates.'}), 500


@app.route('/get_template/<path:template_file_id>', methods=['GET'])
def get_template_route(template_file_id):
    # ... (implementation as before)
    template_file_id = os.path.basename(template_file_id)
    if not template_file_id.endswith(".json"):
        logger.warning(f"Attempt to access non-JSON as template: {template_file_id}")
        return jsonify({"error": "Invalid template format."}), 400
    template_file_path = os.path.join(TEMPLATES_DIR, template_file_id)
    if not os.path.exists(template_file_path):
        logger.error(f"Template not found: {template_file_path}")
        return jsonify({"error": "Template not found."}), 404
    try:
        with open(template_file_path, 'r', encoding='utf-8') as f:
            template_data = json.load(f)
        return jsonify(template_data)
    except Exception as e:
        logger.error(f"Error retrieving template '{template_file_id}': {e}", exc_info=True)
        return jsonify({"error": "Could not read template file."}), 500

@app.route('/apply_learned_preferences', methods=['POST'])
def apply_learned_preferences_route():
    # ... (implementation as before)
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    vendor_name = data.get('vendor_name', '').strip()
    current_mappings_from_client = data.get('current_mappings')
    if not vendor_name:
        return jsonify({"error": "Vendor name is required to apply preferences."}), 400
    if not current_mappings_from_client or not isinstance(current_mappings_from_client, list):
        return jsonify({"error": "Current mappings data is invalid or missing."}), 400
    sanitized_vendor_name = "".join(c if c.isalnum() or c in ('_', '-') else '' for c in vendor_name)
    if not sanitized_vendor_name:
        return jsonify({"error": "Invalid vendor name after sanitization."}), 400
    vendor_filename = f"{sanitized_vendor_name}.json"
    preference_file_path = os.path.join(LEARNED_PREFERENCES_DIR, vendor_filename)
    learned_prefs_map = {}
    if os.path.exists(preference_file_path):
        try:
            with open(preference_file_path, 'r', encoding='utf-8') as f:
                preferences_list = json.load(f)
                if isinstance(preferences_list, list):
                    for pref in preferences_list:
                        if pref.get('original_header') and pref.get('mapped_field'):
                            learned_prefs_map[pref['original_header']] = pref['mapped_field']
                else:
                    logger.warning(f"Preference file {preference_file_path} for {vendor_name} is not a list.")
        except Exception as e_read_pref:
            logger.error(f"Error reading preference file for {vendor_name} at {preference_file_path}: {e_read_pref}", exc_info=True)
    if not learned_prefs_map:
        logger.info(f"No learned preferences found for vendor: {vendor_name}")
        return jsonify({
            'updated_mappings': current_mappings_from_client,
            'vendor_name': vendor_name,
            'message': 'No learned preferences found for this vendor. Mappings unchanged.'
        })
    updated_mappings = []
    applied_count = 0
    for mapping_item in current_mappings_from_client:
        new_mapping_item = mapping_item.copy()
        original_header = mapping_item.get('original_header')
        if original_header in learned_prefs_map:
            preferred_mapped_field = learned_prefs_map[original_header]
            if new_mapping_item.get('mapped_field') != preferred_mapped_field:
                new_mapping_item['mapped_field'] = preferred_mapped_field
                new_mapping_item['confidence_score'] = 99
                new_mapping_item['method'] = 'Learned Preference'
                applied_count +=1
            elif new_mapping_item.get('method') != 'Learned Preference':
                 new_mapping_item['confidence_score'] = max(new_mapping_item.get('confidence_score', 0), 99)
                 new_mapping_item['method'] = 'Learned Verified'
        updated_mappings.append(new_mapping_item)
    logger.info(f"Applied {applied_count} learned preferences for vendor: {vendor_name}")
    return jsonify({
        'updated_mappings': updated_mappings,
        'vendor_name': vendor_name,
        'message': f'Applied {applied_count} learned preferences for {vendor_name}.' if applied_count > 0 else f'Mappings already align with preferences for {vendor_name}.'
        })

@app.route('/get_learned_preferences/<path:vendor_name>', methods=['GET'])
def get_learned_preferences_route(vendor_name):
    original_vendor_name = vendor_name
    sanitized_vendor_name = "".join(c if c.isalnum() or c in ('_', '-') else '' for c in original_vendor_name)
    if not sanitized_vendor_name:
        logger.warning(f"Vendor name '{original_vendor_name}' sanitized to an empty string.")
        return jsonify({'vendor_name': original_vendor_name, 'preferences': [], 'message': 'Invalid vendor name.'}), 200

    vendor_filename = f"{sanitized_vendor_name}.json"
    preference_file_path = os.path.join(LEARNED_PREFERENCES_DIR, vendor_filename)

    if not os.path.exists(preference_file_path):
        logger.info(f"No preference file for vendor: '{original_vendor_name}' at: {preference_file_path}.")
        return jsonify({'vendor_name': original_vendor_name, 'preferences': []})

    try:
        with open(preference_file_path, 'r', encoding='utf-8') as f:
            loaded_data = json.load(f)

        preferences_list = []
        actual_vendor_name_from_file = original_vendor_name # Default to passed name

        if isinstance(loaded_data, dict) and 'preferences' in loaded_data:
            # New format: dict with "original_vendor_name" and "preferences" list
            preferences_list = loaded_data.get('preferences', [])
            actual_vendor_name_from_file = loaded_data.get('original_vendor_name', original_vendor_name)
            if not isinstance(preferences_list, list):
                 logger.error(f"Preference file {vendor_filename} for '{original_vendor_name}' has 'preferences' key but it's not a list.")
                 return jsonify({"error": f"Corrupted data structure in preference file for '{original_vendor_name}'."}), 500
        elif isinstance(loaded_data, list):
            # Old format: file is directly a list of preferences
            logger.warning(f"Old preference file format (list) detected for {vendor_filename} during get. Consider re-saving to update format.")
            preferences_list = loaded_data
            # actual_vendor_name_from_file remains original_vendor_name from route
        else:
            logger.error(f"Preference file {vendor_filename} for '{original_vendor_name}' is neither a list nor the expected dict structure.")
            return jsonify({"error": f"Unexpected data structure in preference file for '{original_vendor_name}'."}), 500

        logger.info(f"Retrieved {len(preferences_list)} preferences for vendor: '{actual_vendor_name_from_file}' (file: {vendor_filename}).")
        return jsonify({'vendor_name': actual_vendor_name_from_file, 'preferences': preferences_list})
    except json.JSONDecodeError:
        logger.error(f"JSON decode error for '{original_vendor_name}' (file: {vendor_filename}).", exc_info=True)
        return jsonify({"error": f"Corrupted preference file (JSON decode error) for '{original_vendor_name}'."}), 500
    except IOError as e:
        logger.error(f"IOError for '{original_vendor_name}' ({preference_file_path}): {e}", exc_info=True)
        return jsonify({"error": f"Could not read preferences for '{original_vendor_name}'."}), 500
    except Exception as e:
        logger.error(f"Unexpected error for '{original_vendor_name}' ({preference_file_path}): {e}", exc_info=True)
        return jsonify({"error": "Unexpected server error retrieving preferences."}), 500

@app.route('/save_learned_preference', methods=['POST'])
def save_learned_preference_route():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    vendor_name = data.get('vendor_name', '').strip() # This is the original, user-provided name
    original_header = data.get('original_header', '').strip()
    mapped_field = data.get('mapped_field', '').strip()

    if not vendor_name or not original_header or not mapped_field:
        missing = [f for f, v in [('vendor_name', vendor_name), ('original_header', original_header), ('mapped_field', mapped_field)] if not v]
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

    if mapped_field == 'N/A': # Do not save 'N/A' as a learned preference
        return jsonify({"status": "info", "message": "Preference not saved for 'N/A' mapping."}), 200

    sanitized_vendor_name_part = "".join(c if c.isalnum() or c in ('_', '-') else '' for c in vendor_name)
    if not sanitized_vendor_name_part:
        logger.warning(f"Vendor name '{vendor_name}' sanitized to empty. Cannot save preference.")
        return jsonify({"error": "Invalid vendor name after sanitization."}), 400

    vendor_filename = f"{sanitized_vendor_name_part}.json"
    preference_file_path = os.path.join(LEARNED_PREFERENCES_DIR, vendor_filename)

    logger.info(f"Saving learned preference for Vendor: '{vendor_name}', Header: '{original_header}' -> '{mapped_field}' into file: {vendor_filename}")

    file_data = {"original_vendor_name": vendor_name, "preferences": []}

    try:
        if os.path.exists(preference_file_path):
            with open(preference_file_path, 'r', encoding='utf-8') as f:
                try:
                    loaded_data = json.load(f)
                    # Check if loaded_data is a dict and has 'preferences' list
                    if isinstance(loaded_data, dict) and isinstance(loaded_data.get('preferences'), list):
                        file_data = loaded_data
                        file_data['original_vendor_name'] = vendor_name # Update in case casing changed etc.
                    else: # Old format (just a list) or corrupted - try to salvage if list, else overwrite
                        if isinstance(loaded_data, list):
                             logger.warning(f"Old preference file format (list) detected for {vendor_filename}. Converting to new dict format.")
                             file_data['preferences'] = loaded_data
                             file_data['original_vendor_name'] = vendor_name # Ensure original name is now stored
                        else:
                             logger.warning(f"Preference file {vendor_filename} was not a list or expected dict. Initializing with new structure.")
                            # file_data is already initialized correctly for this case
                except json.JSONDecodeError:
                    logger.warning(f"Could not decode JSON from {preference_file_path}. Initializing with new structure.")
                    # file_data is already initialized

        preferences_list = file_data.get('preferences', [])
        found_preference = False
        for pref in preferences_list:
            if pref.get('original_header') == original_header:
                pref['mapped_field'] = mapped_field
                pref['last_updated'] = datetime.datetime.utcnow().isoformat() + "Z"
                pref['confirmation_count'] = pref.get('confirmation_count', 0) + 1
                found_preference = True
                break

        if not found_preference:
            preferences_list.append({
                'original_header': original_header,
                'mapped_field': mapped_field,
                'last_updated': datetime.datetime.utcnow().isoformat() + "Z",
                'confirmation_count': 1
            })

        file_data['preferences'] = preferences_list

        with open(preference_file_path, 'w', encoding='utf-8') as f:
            json.dump(file_data, f, indent=4)

        logger.info(f"Successfully saved preference for vendor '{vendor_name}', header '{original_header}' to {vendor_filename}.")
        return jsonify({"status": "success", "message": "Learned preference saved."}), 200

    except Exception as e:
        logger.error(f"Error saving learned preference for vendor '{vendor_name}' to {vendor_filename}: {e}", exc_info=True)
        return jsonify({"error": "Could not save learned preference due to a server error."}), 500

@app.route('/list_vendors_with_preferences', methods=['GET'])
def list_vendors_with_preferences_route():
    vendors_info = []
    if not os.path.exists(LEARNED_PREFERENCES_DIR):
        logger.warning(f"Learned preferences directory '{LEARNED_PREFERENCES_DIR}' not found.")
        return jsonify({'vendors': [], 'message': 'Learned preferences directory not found.'})

    try:
        for f_name in os.listdir(LEARNED_PREFERENCES_DIR):
            if f_name.endswith(".json"):
                preference_file_path = os.path.join(LEARNED_PREFERENCES_DIR, f_name)
                display_name = f_name[:-5] # Default to filename without .json
                try:
                    with open(preference_file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        # New format check: data is dict and has 'original_vendor_name'
                        if isinstance(data, dict) and 'original_vendor_name' in data:
                            display_name = data.get('original_vendor_name', display_name)
                        # Old format check: data is list (no original_vendor_name stored inside)
                        # In this case, display_name remains filename without .json
                        elif isinstance(data, list):
                            logger.info(f"Vendor preference file '{f_name}' is in old list format. Display name will be derived from filename.")
                        else:
                            logger.warning(f"Vendor preference file '{f_name}' has an unexpected structure. Display name will be derived from filename.")

                    vendors_info.append({
                        'display_name': display_name,
                        'vendor_file_id': f_name # Actual filename, e.g., "My_Vendor_Inc.json"
                    })
                except json.JSONDecodeError:
                    logger.error(f"Could not decode JSON from preference file '{f_name}'. Skipping.")
                except Exception as e_file:
                    logger.error(f"Error processing preference file '{f_name}': {e_file}", exc_info=True)

        vendors_info.sort(key=lambda x: x['display_name'].lower())
        return jsonify({'vendors': vendors_info})
    except Exception as e_list:
        logger.error(f"Error listing vendor preferences from '{LEARNED_PREFERENCES_DIR}': {e_list}", exc_info=True)
        return jsonify({'vendors': [], 'error': 'Could not retrieve vendor preferences list.'}), 500

@app.route('/re_extract_headers', methods=['POST'])
def re_extract_headers_route():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "No data provided"}), 400

    file_identifier = data.get('file_identifier')
    file_type = data.get('file_type')
    try:
        skip_rows = int(data.get('skip_rows', 0))
        if skip_rows < 0: skip_rows = 0 # Ensure non-negative
    except ValueError:
        return jsonify({"success": False, "error": "Invalid skip_rows value, must be an integer."}), 400


    if not file_identifier or not file_type:
        missing_fields = []
        if not file_identifier: missing_fields.append('file_identifier')
        if not file_type: missing_fields.append('file_type')
        return jsonify({"success": False, "error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

    if file_type not in ["CSV", "XLSX", "XLS"]: # Only applicable to these types
        return jsonify({"success": False, "error": f"Re-extracting headers with skip_rows is not applicable for file type: {file_type}."}), 400

    file_path_on_disk = os.path.join(app.config['UPLOAD_FOLDER'], file_identifier)
    if not os.path.exists(file_path_on_disk):
        if not os.path.exists(file_identifier): # Check if file_identifier itself is a full path
            logger.error(f"File not found for re-extracting headers: {file_identifier}")
            return jsonify({"success": False, "error": f"File not found: {file_identifier}"}), 404
        file_path_on_disk = file_identifier

    logger.info(f"Re-extracting headers for file: {file_path_on_disk}, type: {file_type}, skipping: {skip_rows} rows.")

    try:
        new_headers_or_error = extract_headers(file_path_on_disk, file_type, skip_rows=skip_rows)

        if isinstance(new_headers_or_error, dict) and "error" in new_headers_or_error:
            logger.error(f"Error re-extracting headers for {file_identifier}: {new_headers_or_error['error']}")
            return jsonify({'success': False, 'error': new_headers_or_error['error'], 'headers': [], 'field_mappings': []}), 400 # Or 500 if server-side

        new_headers = new_headers_or_error # It's a list if no error

        if not new_headers: # Empty list
            return jsonify({'success': True, 'message': 'No headers found with the specified skip_rows.', 'headers': [], 'field_mappings': []})

        # Successfully got new headers, now generate initial mappings for them
        initial_mappings = generate_mappings(new_headers, FIELD_DEFINITIONS)

        return jsonify({
            'success': True,
            'headers': new_headers,
            'field_mappings': initial_mappings,
            'message': f'Headers re-extracted successfully, skipping first {skip_rows} row(s).'
        })

    except Exception as e:
        logger.error(f"Unexpected error in /re_extract_headers for {file_identifier}: {e}", exc_info=True)
        return jsonify({"success": False, "error": "An internal server error occurred while re-extracting headers."}), 500

@app.route('/delete_template/<path:template_filename>', methods=['DELETE'])
def delete_template(template_filename):
    # Basic security check for path traversal or invalid characters
    if '/' in template_filename or '..' in template_filename:
        logger.warning(f"Attempt to delete template with invalid path: {template_filename}")
        return jsonify({'error': 'Invalid template filename.'}), 400

    # Ensure the filename is somewhat sane (e.g., ends with .json, though client should send correct one)
    # For this implementation, we'll rely on the client sending the correct filename as obtained from /list_templates
    # which should include the .json extension.
    if not template_filename.endswith(".json"):
        logger.warning(f"Attempt to delete template without .json extension: {template_filename}")
        # Optionally, append .json, but better if client is consistent.
        # For now, treat as potentially invalid if not ending with .json, or rely on full name from client.
        # Let's assume client sends the filename as listed (which includes .json)
        pass # Assuming template_filename from client is already correct like "MyTemplate.json"

    file_to_delete = os.path.join(TEMPLATES_DIR, template_filename)

    logger.info(f"Attempting to delete template: {file_to_delete}")

    try:
        if os.path.exists(file_to_delete) and os.path.isfile(file_to_delete):
            os.remove(file_to_delete)
            logger.info(f"Successfully deleted template: {template_filename}")
            return jsonify({'status': 'success', 'message': f"Template '{template_filename}' deleted successfully."}), 200
        else:
            logger.warning(f"Template not found for deletion: {template_filename} (path: {file_to_delete})")
            return jsonify({'error': f"Template '{template_filename}' not found."}), 404
    except OSError as e:
        logger.error(f"OSError when trying to delete template '{template_filename}': {e}", exc_info=True)
        return jsonify({'error': f'Failed to delete template due to a storage error: {e.strerror}'}), 500
    except Exception as e:
        logger.error(f"Unexpected error when trying to delete template '{template_filename}': {e}", exc_info=True)
        return jsonify({'error': 'Failed to delete template due to an unexpected server error.'}), 500

@app.route('/delete_vendor_preferences/<path:vendor_name>', methods=['DELETE'])
def delete_vendor_preferences(vendor_name):
    original_vendor_name = vendor_name # Keep original for messages

    # Sanitize vendor_name to create a safe filename
    sanitized_name_part = "".join(c if c.isalnum() or c in ('_', '-') else '' for c in original_vendor_name)

    if not sanitized_name_part: # Check if sanitization resulted in an empty string
        logger.warning(f"Attempt to delete preferences for vendor '{original_vendor_name}' which sanitized to an empty filename part.")
        return jsonify({'error': 'Invalid vendor name provided (results in empty filename).'}), 400

    vendor_filename = f"{sanitized_name_part}.json"
    preference_file_to_delete = os.path.join(LEARNED_PREFERENCES_DIR, vendor_filename)

    logger.info(f"Attempting to delete learned preferences for vendor '{original_vendor_name}' (file: {vendor_filename}) at path: {preference_file_to_delete}")

    try:
        if os.path.exists(preference_file_to_delete) and os.path.isfile(preference_file_to_delete):
            os.remove(preference_file_to_delete)
            logger.info(f"Successfully deleted preferences file: {vendor_filename} for vendor: {original_vendor_name}")
            return jsonify({
                'status': 'success',
                'message': f"All learned preferences for vendor '{original_vendor_name}' (file: '{vendor_filename}') deleted successfully."
            }), 200
        else:
            logger.warning(f"Preference file not found for vendor '{original_vendor_name}' (file: {vendor_filename}) at path: {preference_file_to_delete}")
            return jsonify({
                'error': f"No learned preferences found for vendor '{original_vendor_name}' (file: '{vendor_filename}')."
            }), 404
    except OSError as e:
        logger.error(f"OSError when trying to delete preference file '{vendor_filename}' for vendor '{original_vendor_name}': {e}", exc_info=True)
        return jsonify({'error': f'Failed to delete vendor preferences due to a storage error: {e.strerror}'}), 500
    except Exception as e:
        logger.error(f"Unexpected error when trying to delete preference file '{vendor_filename}' for vendor '{original_vendor_name}': {e}", exc_info=True)
        return jsonify({'error': 'Failed to delete vendor preferences due to an unexpected server error.'}), 500

@app.route('/delete_specific_vendor_preference', methods=['POST'])
def delete_specific_vendor_preference():
    data = request.get_json()
    if not data:
        logger.warning("Request to /delete_specific_vendor_preference with no JSON data.")
        return jsonify({"error": "No data provided"}), 400

    original_vendor_name = data.get('vendor_name', '').strip()
    original_header = data.get('original_header', '').strip()

    if not original_vendor_name or not original_header:
        missing_fields = []
        if not original_vendor_name: missing_fields.append("vendor_name")
        if not original_header: missing_fields.append("original_header")
        logger.warning(f"Missing fields in /delete_specific_vendor_preference: {', '.join(missing_fields)}")
        return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

    # Sanitize vendor_name to create a safe filename
    sanitized_name_part = "".join(c if c.isalnum() or c in ('_', '-') else '' for c in original_vendor_name)

    if not sanitized_name_part:
        logger.warning(f"Vendor name '{original_vendor_name}' sanitized to empty for specific preference deletion.")
        return jsonify({'error': 'Invalid vendor name provided (results in empty filename).'}), 400

    vendor_filename = f"{sanitized_name_part}.json"
    preference_file_path = os.path.join(LEARNED_PREFERENCES_DIR, vendor_filename)

    logger.info(f"Attempting to delete specific preference: Header '{original_header}' for Vendor '{original_vendor_name}' (File: {vendor_filename})")

    if not (os.path.exists(preference_file_path) and os.path.isfile(preference_file_path)):
        logger.warning(f"Preference file not found for vendor '{original_vendor_name}' (File: {vendor_filename}) when trying to delete specific preference.")
        return jsonify({'error': f"No preferences found for vendor '{original_vendor_name}'."}), 404

    try:
        with open(preference_file_path, 'r', encoding='utf-8') as f:
            preferences_list = json.load(f)
            if not isinstance(preferences_list, list): # Should be a list of dicts
                logger.error(f"Preference file {vendor_filename} for vendor {original_vendor_name} is corrupted (not a list).")
                return jsonify({'error': 'Preference file is corrupted.'}), 500
    except json.JSONDecodeError:
        logger.error(f"JSON decode error for preference file {vendor_filename} (Vendor: {original_vendor_name}).", exc_info=True)
        return jsonify({'error': 'Could not parse preference file.'}), 500
    except IOError as e:
        logger.error(f"IOError reading preference file {vendor_filename} (Vendor: {original_vendor_name}): {e}", exc_info=True)
        return jsonify({'error': 'Could not read preference file.'}), 500
    except Exception as e: # Catch any other unexpected error during file read
        logger.error(f"Unexpected error reading preference file {vendor_filename} (Vendor: {original_vendor_name}): {e}", exc_info=True)
        return jsonify({'error': 'An unexpected server error occurred while reading preferences.'}), 500

    original_length = len(preferences_list)
    # Filter out the specific preference
    preferences_list = [pref for pref in preferences_list if pref.get('original_header') != original_header]
    preference_found_and_removed = len(preferences_list) < original_length

    if preference_found_and_removed:
        try:
            if not preferences_list: # List is now empty
                os.remove(preference_file_path)
                logger.info(f"Removed empty preference file {vendor_filename} for vendor '{original_vendor_name}' after deleting last specific preference.")
                message = f"Preference for header '{original_header}' deleted. All preferences for vendor '{original_vendor_name}' are now cleared as the list was empty."
            else:
                with open(preference_file_path, 'w', encoding='utf-8') as f:
                    json.dump(preferences_list, f, indent=4)
                logger.info(f"Successfully deleted preference for header '{original_header}' for vendor '{original_vendor_name}' in file {vendor_filename}.")
                message = f"Preference for header '{original_header}' for vendor '{original_vendor_name}' deleted successfully."

            return jsonify({'status': 'success', 'message': message}), 200

        except OSError as e:
            logger.error(f"OSError when saving/deleting preference file {vendor_filename} (Vendor: {original_vendor_name}) after modification: {e}", exc_info=True)
            return jsonify({'error': f'Failed to update preference file due to a storage error: {e.strerror}'}), 500
        except Exception as e: # Catch any other unexpected error during file write/delete
            logger.error(f"Unexpected error saving/deleting preference file {vendor_filename} (Vendor: {original_vendor_name}) after modification: {e}", exc_info=True)
            return jsonify({'error': 'An unexpected server error occurred while updating preferences.'}), 500
    else:
        logger.warning(f"No preference found for header '{original_header}' for vendor '{original_vendor_name}' (File: {vendor_filename}). No changes made.")
        return jsonify({'error': f"No preference found for header '{original_header}' for vendor '{original_vendor_name}'."}), 404

if __name__ == "__main__":
    app.run(debug=True)

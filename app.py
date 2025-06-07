from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import magic
import logging
import json
import datetime # For timestamping templates
from file_parser import extract_headers, extract_data
from azure_openai_client import test_azure_openai_connection, azure_openai_configured
from header_mapper import generate_mappings
from chatbot_service import get_mapping_suggestions
# from werkzeug.utils import secure_filename # Option for more robust filename sanitization

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB limit
TEMPLATES_DIR = "templates_storage"


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

SUPPORTED_MIME_TYPES = {
    'application/pdf': 'PDF',
    'application/vnd.ms-excel': 'XLS',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'XLSX',
    'text/csv': 'CSV'
}

@app.route('/')
def index():
    return render_template('index.html', field_definitions_json=json.dumps(FIELD_DEFINITIONS))

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
            results_entry = {"filename": filename, "success": False, "message": "File processing started.", "file_type": "unknown", "headers": [], "field_mappings": []}
            try:
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file_storage.save(file_path)

                try:
                    mime_type = magic.from_file(file_path, mime=True)
                    detected_type_name = SUPPORTED_MIME_TYPES.get(mime_type)
                    if detected_type_name:
                        results_entry["file_type"] = detected_type_name
                        results_entry["success"] = True
                        results_entry["message"] = "Upload successful."
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

                if results_entry["success"] and results_entry["file_type"] in ["CSV", "XLSX", "XLS"]:
                    headers_extraction_result = extract_headers(file_path, results_entry["file_type"])
                    if isinstance(headers_extraction_result, list):
                        results_entry["headers"] = headers_extraction_result
                        if headers_extraction_result:
                            mappings = generate_mappings(headers_extraction_result, FIELD_DEFINITIONS)
                            results_entry["field_mappings"] = mappings
                            logger.info(f"Generated {len(mappings)} field mappings for {filename}.")
                        else: # No headers found in file
                            results_entry["message"] += " (No headers found in file)"
                    elif isinstance(headers_extraction_result, dict) and "error" in headers_extraction_result:
                        results_entry["success"] = False
                        results_entry["message"] = headers_extraction_result["error"]
                elif results_entry["success"] and results_entry["file_type"] == "PDF":
                    pdf_header_info = extract_headers(file_path, results_entry["file_type"])
                    if isinstance(pdf_header_info, dict) and "info" in pdf_header_info:
                         results_entry["message"] += f" ({pdf_header_info['info']})"

                results.append(results_entry)

            except Exception as e_save:
                results.append({"filename": filename, "success": False, "message": f"Error saving file: {str(e_save)}", "file_type": "error_saving", "headers": [], "field_mappings": []})

            log_message = (f"File: {filename}, Status: {'Success' if results_entry['success'] else 'Failure'}, Type: {results_entry['file_type']}, "
                           f"Message: {results_entry['message']}, Headers: {len(results_entry['headers'])}, Mappings: {len(results_entry['field_mappings'])}")
            logger.info(log_message)

    if uploaded_file_count == 0 and len(results) > 0: # Check if any file was successfully uploaded
        # If all files failed at upload/type detection stage, this could be a 400 or a 200 with detailed errors
        pass # Fall through to return results, which will contain error details for each file

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
    if not all([file_identifier, finalized_mappings, file_type]):
        return jsonify({"error": "Missing required fields"}), 400
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_identifier)
    if not os.path.exists(file_path):
        if not os.path.exists(file_identifier): # Check if full path was sent
            logger.error(f"File not found: {file_identifier}")
            return jsonify({"error": f"File not found: {file_identifier}"}), 404
        file_path = file_identifier
    logger.info(f"Processing data for: {file_path}, type: {file_type}")
    try:
        extracted_data = extract_data(file_path, file_type, finalized_mappings)
        if isinstance(extracted_data, dict) and "error" in extracted_data:
            logger.error(f"Data extraction error for {file_path}: {extracted_data['error']}")
            return jsonify(extracted_data), 400
        return jsonify({'data': extracted_data, 'message': f'Processed {len(extracted_data)} records.' if isinstance(extracted_data, list) else 'Data processed.'})
    except Exception as e:
        logger.error(f"File processing error for {file_path}: {e}", exc_info=True)
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
    if not data: return jsonify({"error": "No data provided"}), 400
    original_template_name = data.get('template_name', '').strip()
    field_mappings = data.get('field_mappings')
    if not original_template_name: return jsonify({"error": "Template name required."}), 400
    if not field_mappings or not isinstance(field_mappings, list) or not field_mappings:
        return jsonify({"error": "Field mappings required."}), 400
    sanitized_name = "".join(c if c.isalnum() or c in ('_', '-') else '' for c in original_template_name)
    if not sanitized_name: sanitized_name = "unnamed_template"
    filename = f"{sanitized_name}.json"
    template_file_path = os.path.join(TEMPLATES_DIR, filename)
    template_data = {"template_name": original_template_name, "filename": filename,
                     "creation_timestamp": datetime.datetime.utcnow().isoformat() + "Z", "field_mappings": field_mappings}
    try:
        with open(template_file_path, 'w', encoding='utf-8') as f:
            json.dump(template_data, f, indent=4)
        logger.info(f"Template '{original_template_name}' saved as '{filename}'.")
        return jsonify({"status": "success", "message": "Template saved.", "template_name": original_template_name, "filename": filename}), 201
    except IOError as e:
        logger.error(f"IOError saving template '{filename}': {e}", exc_info=True)
        return jsonify({"error": f"Could not save template: {str(e)}"}), 500
    except Exception as e:
        logger.error(f"Error saving template '{filename}': {e}", exc_info=True)
        return jsonify({"error": "Server error saving template."}), 500

@app.route('/list_templates', methods=['GET'])
def list_templates_route():
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
                        file_id = template_data.get('filename', f_name)
                        if display_name and file_id:
                            templates_info.append({'display_name': display_name, 'file_id': file_id})
                        else:
                            logger.warning(f"Skipping template '{f_name}': missing name/filename key.")
                except Exception as e_file:
                    logger.error(f"Error processing template file '{f_name}': {e_file}", exc_info=True)
        templates_info.sort(key=lambda x: x['display_name'].lower())
        return jsonify({'templates': templates_info})
    except Exception as e_list:
        logger.error(f"Error listing templates from '{TEMPLATES_DIR}': {e_list}", exc_info=True)
        return jsonify({'templates': [], 'error': 'Could not retrieve templates.'}), 500

@app.route('/get_template/<path:template_file_id>', methods=['GET'])
def get_template_route(template_file_id):
    template_file_id = os.path.basename(template_file_id) # Security: ensure it's just a filename
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
        return jsonify(template_data) # Returns full template content
    except Exception as e:
        logger.error(f"Error retrieving template '{template_file_id}': {e}", exc_info=True)
        return jsonify({"error": "Could not read template file."}), 500

if __name__ == "__main__":
    app.run(debug=True)

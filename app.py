from flask import Flask, render_template, request, jsonify
import os
import magic
import logging
import json # For loading field definitions
from file_parser import extract_headers
from azure_openai_client import test_azure_openai_connection, azure_openai_configured
from header_mapper import generate_mappings
from chatbot_service import get_mapping_suggestions # Import the chatbot service

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB limit

# --- Field Definitions ---
FIELD_DEFINITIONS = {}

def load_field_definitions():
    global FIELD_DEFINITIONS
    try:
        with open('field_definitions.json', 'r', encoding='utf-8') as f:
            FIELD_DEFINITIONS = json.load(f)
        # Optionally, log success or print for verification during startup
        # print("Field definitions loaded successfully.")
        # logger.info("Field definitions loaded successfully.") # If logger is configured before this call
    except FileNotFoundError:
        # print("Error: field_definitions.json not found. Using empty definitions.", file=sys.stderr)
        logging.error("CRITICAL: field_definitions.json not found. Field mapping will not work.")
        FIELD_DEFINITIONS = {} # Ensure it's empty if file not found
    except json.JSONDecodeError:
        # print("Error: field_definitions.json is not valid JSON. Using empty definitions.", file=sys.stderr)
        logging.error("CRITICAL: field_definitions.json is not valid JSON. Field mapping will not work.")
        FIELD_DEFINITIONS = {} # Ensure it's empty if JSON is invalid
    except Exception as e:
        logging.error(f"CRITICAL: An unexpected error occurred loading field_definitions.json: {e}")
        FIELD_DEFINITIONS = {}


# --- Logger Setup ---
logger = logging.getLogger('upload_history')
logger.setLevel(logging.INFO)
file_handler_configured = False
if logger.handlers: # Check if handlers already exist from a previous context (e.g. module reload)
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

load_field_definitions() # Load definitions *after* logger setup

# --- Test Azure OpenAI Connection (Optional) ---
# This is done after logger and other configs are set up.
# The application should not crash if this fails.
try:
    logger.info("Attempting to test Azure OpenAI connection...")
    test_result = test_azure_openai_connection()
    logger.info(f"Azure OpenAI Connection Test Result: {test_result}")
    if not test_result.get("success"):
        logger.warning(f"Azure OpenAI connection test failed: {test_result.get('message')} - Details: {test_result.get('details')}")
    # The azure_openai_configured variable from azure_openai_client.py can also be checked here if needed
    if not azure_openai_configured:
        logger.warning("Azure OpenAI client is not configured due to missing environment variables or initialization failure.")
except Exception as e:
    logger.error(f"An unexpected error occurred during the Azure OpenAI connection test call: {e}", exc_info=True)
# --- End Azure OpenAI Connection Test ---


SUPPORTED_MIME_TYPES = {
    'application/pdf': 'PDF',
    'application/vnd.ms-excel': 'XLS',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'XLSX',
    'text/csv': 'CSV'
}

@app.route('/')
def index():
    # Pass FIELD_DEFINITIONS to the template, ensuring it's JSON-serializable
    return render_template('index.html', field_definitions_json=json.dumps(FIELD_DEFINITIONS))

@app.route('/upload', methods=['POST'])
def upload_files():
    files = request.files.getlist('files[]')
    results = []
    uploaded_file_count = 0

    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    # First check: total number of files
    if len(files) > 10:
        for file_storage in files: # Iterate over FileStorage objects
            results.append({
                "filename": file_storage.filename if file_storage else "Unknown",
                "success": False,
                "message": "Too many files uploaded (limit is 10). Upload cancelled for all files.",
                "file_type": "N/A"
            })
        return jsonify(results), 400

    # Check if any file is actually submitted
    if not any(file_storage and file_storage.filename for file_storage in files):
        return jsonify([{
            "filename": "N/A",
            "success": False,
            "message": "No files selected or files are empty.",
            "file_type": "N/A"
        }]), 400


    for file_storage in files:
        if file_storage and file_storage.filename: # Ensure file object and filename exist
            filename = file_storage.filename
            file_type = "unknown"
            message = ""
            success = False

            try:
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

                # Save before type checking to have access to the content on disk
                # Alternatively, read into a buffer: file_storage.stream.read(FIRST_CHUNK_SIZE)
                # but saving first is simpler if files are definitely going to be saved.
                file_storage.save(file_path)

                # Detect MIME type
                try:
                    mime_type = magic.from_file(file_path, mime=True)
                    detected_type_name = SUPPORTED_MIME_TYPES.get(mime_type)

                    if detected_type_name:
                        file_type = detected_type_name
                        success = True
                        message = "Upload successful."
                        uploaded_file_count += 1
                    else:
                        success = False
                        message = f"Unsupported file type: {mime_type}. Supported types are PDF, XLSX, XLS, CSV."
                        file_type = mime_type # Store the actual detected mime type if unsupported
                        # Optionally, delete the unsupported file: os.remove(file_path)
                except magic.MagicException as me: # Specific exception for python-magic
                    success = False
                    message = "Error detecting file type. The file may be corrupted or in an unreadable format."
                    file_type = "error_detection"
                    # Optionally, delete the problematic file: os.remove(file_path)
                except Exception as e_detect: # Catch other potential errors during detection
                    success = False
                    message = f"Error during file type detection: {str(e_detect)}"
                    file_type = "error_detection_general"

                results_entry = {
                    "filename": filename,
                    "success": success,
                    "message": message,
                    "file_type": file_type,
                    "headers": [], # Initialize headers field
                    "field_mappings": [] # Initialize field_mappings
                }

                if success and file_type in ["CSV", "XLSX", "XLS"]:
                    headers_extraction_result = extract_headers(file_path, file_type) # Renamed for clarity
                    if isinstance(headers_extraction_result, list):
                        results_entry["headers"] = headers_extraction_result
                        if headers_extraction_result: # If headers were actually extracted
                            # Generate field mappings
                            mappings = generate_mappings(headers_extraction_result, FIELD_DEFINITIONS)
                            results_entry["field_mappings"] = mappings
                            # Optionally, log mapping generation success/details
                            logger.info(f"Generated {len(mappings)} field mappings for {filename}.")
                        # else: message remains "Upload successful", headers list is empty
                    elif isinstance(headers_extraction_result, dict) and "error" in headers_extraction_result:
                        results_entry["success"] = False # Header extraction failed
                        results_entry["message"] = headers_extraction_result["error"]
                    elif isinstance(headers_extraction_result, dict) and "info" in headers_extraction_result:
                        results_entry["message"] += f" ({headers_extraction_result['info']})"

                # If file type is PDF, and was successful so far (type detection)
                elif success and file_type == "PDF":
                    pdf_header_info = extract_headers(file_path, file_type) # This returns an info message
                    if isinstance(pdf_header_info, dict) and "info" in pdf_header_info:
                         results_entry["message"] += f" ({pdf_header_info['info']})"


                results.append(results_entry)

            except Exception as e_save: # Errors during file.save()
                results.append({
                    "filename": filename,
                    "success": False,
                    "message": f"Error saving file: {str(e_save)}",
                    "file_type": "error_saving"
                })

            # Log the result for this file (using the state from results_entry)
            final_status = results_entry['success']
            final_message = results_entry['message']
            final_file_type = results_entry['file_type'] # This should be the originally detected type

            log_message = (
                f"File: {filename}, "
                f"Status: {'Success' if final_status else 'Failure'}, "
                f"Type: {final_file_type}, "
                f"Message: {final_message}, "
                f"Headers Count: {len(results_entry.get('headers', []))}, "
                f"Mappings Count: {len(results_entry.get('field_mappings', []))}"
            )
            logger.info(log_message)

        # This else block might be redundant if using getlist and files always have a filename if present
        # else:
        #     results.append({
        #         "filename": "Unknown",
        #         "success": False,
        #         "message": "No file selected or file is empty.",
        #         "file_type": "N/A"
        #     })

    if uploaded_file_count == 0 and not any(r['success'] for r in results) and len(results) > 0 :
         # If no files were successfully uploaded and there are results, likely all failed some check
        return jsonify(results), 400 # Or 200 if partial success is an option for some files
    elif not results: # Should be caught by the "no files selected" check earlier
        return jsonify([{
            "filename": "N/A",
            "success": False,
            "message": "No files processed.", # Should not happen if files were submitted
            "file_type": "N/A"
        }]), 400


    return jsonify(results)

@app.route('/chatbot_suggest_mapping', methods=['POST'])
def chatbot_suggest_mapping_route():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    original_header = data.get('original_header')
    current_mapped_field = data.get('current_mapped_field')

    if not original_header:
        return jsonify({"error": "Missing 'original_header' in request"}), 400
    # current_mapped_field can be N/A or missing, which is fine

    logger.info(f"Received chatbot suggestion request for header: '{original_header}', current map: '{current_mapped_field}'")

    try:
        suggestions = get_mapping_suggestions(original_header, current_mapped_field, FIELD_DEFINITIONS)
        return jsonify(suggestions)
    except Exception as e:
        logger.error(f"Error in /chatbot_suggest_mapping route for header '{original_header}': {e}", exc_info=True)
        return jsonify({"error": "An internal error occurred while generating suggestions."}), 500


if __name__ == "__main__":
    app.run(debug=True)

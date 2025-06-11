from flask import Flask, render_template, request, jsonify, send_from_directory, send_file, current_app
import os
import io
import magic
import logging
import json
import datetime
import pandas as pd
import re # Added import for regular expressions
from file_parser import extract_headers, extract_data, extract_headers_from_pdf_tables
from azure_openai_client import test_azure_openai_connection, azure_openai_configured
from data_validator import validate_uniqueness, validate_invoice_via_api # Import new validation functions
# from werkzeug.utils import secure_filename
import csv
from pdftocsv import extract_tables_from_file # Added for PDF to CSV conversion

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

# Load field definitions first
load_field_definitions()

# Import modules that depend on FIELD_DEFINITIONS AFTER it's loaded
import header_mapper
import chatbot_service

# Initialize these modules with the loaded field definitions
header_mapper.initialize_header_mapper(FIELD_DEFINITIONS)
chatbot_service.initialize_chatbot_service(FIELD_DEFINITIONS)


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
    'text/csv': 'CSV',
    'text/plain': 'CSV',  # Add text/plain as a CSV type
    'application/octet-stream': 'XLS' # Added for fallback
}

# Map extensions to our internal type names for fallback
EXTENSION_TO_TYPE_FALLBACK = {
    '.csv': 'CSV',
    '.xls': 'XLS',
    '.xlsx': 'XLSX',
    '.pdf': 'PDF'
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
    files = request.files.getlist('files[]') # Ensure this matches your frontend key
    results = []

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
            original_filename_for_vendor = file_storage.filename # Store original filename for vendor matching and PDF caching
            filename = file_storage.filename # This might change if PDF is converted
            results_entry = {
                "filename": filename, "success": False, "message": "File processing started.",
                "file_type": "unknown", "headers": [], "field_mappings": [],
                "applied_template_name": None, # For auto-applied template
                "applied_template_filename": None, # For auto-applied template
                "skip_rows": 0 # Default, to be overridden by template
            }
            try:
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file_storage.save(file_path)

                try:
                    raw_mime_type = magic.from_file(file_path, mime=True)
                    logger.info(f"[UPLOAD_DEBUG] Raw MIME type for {filename}: '{raw_mime_type}'")
                    
                    mime_type = raw_mime_type.lower() if raw_mime_type else None
                    logger.info(f"[UPLOAD_DEBUG] Normalized (lowercase) MIME type: '{mime_type}'")

                    detected_type_name = SUPPORTED_MIME_TYPES.get(mime_type)
                    logger.info(f"[UPLOAD_DEBUG] Initial detected_type_name from SUPPORTED_MIME_TYPES: '{detected_type_name}' (for mime_type '{mime_type}')")
                    
                    effective_filename_for_processing = filename
                    effective_file_path_for_processing = file_path

                    if detected_type_name == 'OCTET_STREAM': # Corrected from 'XLS' to 'OCTET_STREAM' for comparison
                        logger.info(f"[UPLOAD_DEBUG] MIME type is application/octet-stream for {filename}. Attempting fallback using file extension.")
                        _, file_extension = os.path.splitext(filename)
                        file_extension_lower = file_extension.lower()
                        logger.info(f"[UPLOAD_DEBUG] File extension: '{file_extension}', Lowercase for fallback: '{file_extension_lower}'")
                        
                        fallback_type_name = EXTENSION_TO_TYPE_FALLBACK.get(file_extension_lower)
                        logger.info(f"[UPLOAD_DEBUG] Fallback type from EXTENSION_TO_TYPE_FALLBACK: '{fallback_type_name}' for ext '{file_extension_lower}'")

                        if fallback_type_name:
                            logger.info(f"[UPLOAD_DEBUG] Fallback successful: Using type '{fallback_type_name}' for extension '{file_extension_lower}'. Updating detected_type_name.")
                            detected_type_name = fallback_type_name
                        else:
                            logger.warning(f"[UPLOAD_DEBUG] Fallback failed: Extension '{file_extension_lower}' is not recognized for octet-stream. detected_type_name remains 'OCTET_STREAM'.")
                    
                    logger.info(f"[UPLOAD_DEBUG] Final detected_type_name after potential fallback: '{detected_type_name}'")
                    
                    is_processable_type = detected_type_name and detected_type_name != 'OCTET_STREAM' # Ensure OCTET_STREAM itself is not processable
                    logger.info(f"[UPLOAD_DEBUG] Is processable type? {is_processable_type} (based on detected_type_name: '{detected_type_name}')")

                    if is_processable_type:
                        results_entry["file_type"] = detected_type_name
                        results_entry["success"] = True 
                        results_entry["message"] = "Upload and type detection successful."

                        if detected_type_name == "PDF":
                            try:
                                pdf_filename_base = os.path.splitext(filename)[0]
                                csv_output_filename = f"{pdf_filename_base}-converted.csv"
                                csv_output_path = os.path.join(app.config['UPLOAD_FOLDER'], csv_output_filename)
                                
                                logger.info(f"PDF detected. Attempting to convert '{filename}' to CSV at '{csv_output_path}'.")
                                extract_tables_from_file(file_path, csv_output_path) 
                                
                                if os.path.exists(csv_output_path):
                                    logger.info(f"Successfully converted PDF '{filename}' to CSV: '{csv_output_filename}'.")
                                    effective_file_path_for_processing = csv_output_path
                                    effective_filename_for_processing = csv_output_filename # Use this for further processing
                                    results_entry["file_type"] = "CSV" 
                                    results_entry["filename"] = csv_output_filename 
                                    results_entry["original_pdf_filename"] = original_filename_for_vendor # Keep track of original PDF name
                                    results_entry["message"] = "PDF successfully converted to CSV and uploaded."
                                    detected_type_name = "CSV" 
                                else:
                                    logger.warning(f"PDF to CSV conversion for '{filename}' did not produce output. Proceeding with direct PDF extraction.")
                            except Exception as e_pdf_to_csv:
                                logger.error(f"Error converting PDF '{filename}' to CSV: {e_pdf_to_csv}", exc_info=True)
                                results_entry["message"] += f" (Note: PDF to CSV conversion failed: {str(e_pdf_to_csv)})"
                    
                    else: 
                        final_error_message = f"Unsupported file type (Reported MIME: {raw_mime_type}"
                        current_file_extension_for_msg = os.path.splitext(filename)[1].lower()
                        if mime_type == 'application/octet-stream':
                            if detected_type_name == 'OCTET_STREAM': # Explicitly check if it remained OCTET_STREAM
                                final_error_message += f", extension '{current_file_extension_for_msg}' not recognized for fallback"
                            # else: if it was octet-stream but fallback gave a non-processable type, this is covered by generic 'else' below
                        elif not detected_type_name: # MIME type not in SUPPORTED_MIME_TYPES
                            final_error_message += ", MIME type not configured as supported"
                        # else: detected_type_name is something else not processable (e.g. if we add more types to SUPPORTED_MIME_TYPES but don't handle them)
                        # This 'else' branch (is_processable_type is False) implies detected_type_name is None or 'OCTET_STREAM' or other unhandled
                        final_error_message += ")."
                        
                        results_entry["message"] = final_error_message
                        results_entry["file_type"] = raw_mime_type 
                        results_entry["success"] = False
                
                except magic.MagicException as e_magic:
                    logger.error(f"MagicException for {original_filename_for_vendor}: {e_magic}", exc_info=True)
                    results_entry["message"] = "Error detecting file type (file may be corrupted or inaccessible)."
                    results_entry["file_type"] = "error_detection_magic"
                    results_entry["success"] = False
                except Exception as e_detect: 
                    logger.error(f"Error during file type detection phase for {original_filename_for_vendor}: {e_detect}", exc_info=True)
                    results_entry["message"] = f"Error during file type detection: {str(e_detect)}"
                    results_entry["file_type"] = "error_detection_general"
                    results_entry["success"] = False

                # === Start of New/Modified Header Extraction and Template Logic ===
                if results_entry["success"] and detected_type_name in ["CSV", "XLSX", "XLS", "PDF"]:
                    logger.info(f"Processing headers and mappings for: {effective_filename_for_processing} (Type: {detected_type_name}), Original: {original_filename_for_vendor}")

                    template_applied_data = None
                    current_skip_rows_for_extraction = 0 # Default for header extraction

                    # 1. Extract Vendor Name from original filename
                    vendor_name_from_file = ""
                    if original_filename_for_vendor:
                        name_without_extension = os.path.splitext(original_filename_for_vendor)[0]
                        # Split by the first occurrence of space, underscore, or hyphen
                        parts = re.split(r'[ _-]', name_without_extension, 1)
                        if parts: vendor_name_from_file = parts[0]

                    # 2. Search for and load Template
                    if vendor_name_from_file and os.path.exists(TEMPLATES_DIR):
                        logger.info(f"Attempting to find template for vendor: '{vendor_name_from_file}' from filename '{original_filename_for_vendor}'")
                        normalized_vendor_name = vendor_name_from_file.lower()
                        for template_file_in_storage in os.listdir(TEMPLATES_DIR):
                            template_base_name = os.path.splitext(template_file_in_storage)[0]
                            if template_base_name.lower() == normalized_vendor_name and template_file_in_storage.endswith(".json"):
                                try:
                                    template_path = os.path.join(TEMPLATES_DIR, template_file_in_storage)
                                    with open(template_path, 'r', encoding='utf-8') as f_tpl:
                                        loaded_template = json.load(f_tpl)
                                    if "field_mappings" in loaded_template: # Basic validation
                                        template_applied_data = loaded_template
                                        current_skip_rows_for_extraction = loaded_template.get("skip_rows", 0)
                                        results_entry["skip_rows"] = current_skip_rows_for_extraction # Set for response
                                        results_entry["applied_template_name"] = loaded_template.get("template_name", template_base_name)
                                        results_entry["applied_template_filename"] = template_file_in_storage
                                        logger.info(f"Found template '{template_file_in_storage}' for vendor '{vendor_name_from_file}'. Will use its skip_rows: {current_skip_rows_for_extraction}.")
                                        break # Stop searching once a template is found
                                except Exception as e_tpl_load:
                                    logger.error(f"Error loading template {template_file_in_storage} for {vendor_name_from_file}: {e_tpl_load}")
                    
                    # 3. Extract Actual Headers from file
                    actual_headers_from_file = []
                    # `file_path` is the path to the original uploaded file (e.g., original.pdf)
                    # `effective_file_path_for_processing` is the path to the file to be parsed (e.g., original-converted.csv or original.xlsx)
                    
                    if detected_type_name == "PDF": # This means direct PDF extraction (conversion failed or was not applicable)
                        # Use original PDF path: `file_path`
                        headers_extraction_result_dict = extract_headers_from_pdf_tables(file_path) 
                        if isinstance(headers_extraction_result_dict, dict) and "error" not in headers_extraction_result_dict:
                            actual_headers_from_file = headers_extraction_result_dict.get("headers", [])
                            pdf_data_rows = headers_extraction_result_dict.get("data_rows")
                            if actual_headers_from_file and pdf_data_rows is not None:
                                TEMP_PDF_DATA_FOR_EXTRACTION[original_filename_for_vendor] = {
                                   'headers': actual_headers_from_file,
                                   'data_rows': pdf_data_rows
                                }
                                logger.info(f"Cached 'data_rows' for PDF {original_filename_for_vendor}. Headers: {len(actual_headers_from_file)}, Rows: {len(pdf_data_rows)}")
                        elif isinstance(headers_extraction_result_dict, dict) and "error" in headers_extraction_result_dict:
                            results_entry["success"] = False # Mark failure at this stage
                            results_entry["message"] = headers_extraction_result_dict["error"]
                        else: # Unexpected result from PDF header extraction
                            results_entry["success"] = False
                            results_entry["message"] = "Unexpected result from PDF header extraction."

                    else: # CSV, XLSX, XLS (detected_type_name is "CSV", "XLSX", or "XLS")
                        # Use `effective_file_path_for_processing` and `current_skip_rows_for_extraction`
                        headers_list_or_error_dict = extract_headers(effective_file_path_for_processing, detected_type_name, skip_rows=current_skip_rows_for_extraction)
                        if isinstance(headers_list_or_error_dict, list):
                            actual_headers_from_file = headers_list_or_error_dict
                        elif isinstance(headers_list_or_error_dict, dict) and "error" in headers_list_or_error_dict:
                            results_entry["success"] = False # Mark failure
                            results_entry["message"] = headers_list_or_error_dict["error"]
                        else: # Unexpected result
                            results_entry["success"] = False
                            results_entry["message"] = "Unexpected result from header extraction for tabular file."
                            
                    results_entry["headers"] = actual_headers_from_file

                    # 4. Determine Field Mappings (Template or Auto-generated), only if header extraction was successful
                    if results_entry["success"]: # Check if header extraction above was successful
                        if actual_headers_from_file: # If headers were found
                            if template_applied_data:
                                results_entry["field_mappings"] = template_applied_data.get("field_mappings", [])
                                # results_entry["skip_rows"] is already set from template
                                results_entry["message"] = f"Template '{results_entry['applied_template_name']}' auto-applied with {results_entry['skip_rows']} skip rows."
                                logger.info(f"Applied template mappings for '{original_filename_for_vendor}'.")
                            else: # No template applied, generate mappings
                                mappings = header_mapper.generate_mappings(actual_headers_from_file, FIELD_DEFINITIONS)
                                results_entry["field_mappings"] = mappings
                                # results_entry["skip_rows"] remains default 0 if no template
                                results_entry["message"] = "Headers extracted and auto-mapped." # Default message
                                logger.info(f"Generated {len(mappings)} mappings for {original_filename_for_vendor} (Type: {detected_type_name}).")
                        else: # No headers found in file, but header extraction itself didn't error
                            current_msg = results_entry.get("message", "")
                            if "successfully" in current_msg.lower() or "auto-mapped" in current_msg.lower() : # Avoid double "no headers" if already part of a success message
                                results_entry["message"] = current_msg + " However, no headers were found/extracted."
                            else:
                                results_entry["message"] = (current_msg + " No headers were found/extracted.").strip()
                            # field_mappings will be empty. If a template was "applied" but file has no headers, template mappings might be misleading.
                            # For now, if template_applied_data exists, its mappings are used.
                            if template_applied_data: # A template was found, but file has no headers
                                results_entry["message"] = f"Template '{results_entry['applied_template_name']}' was found, but no headers were extracted from the file."
                                # Keep template mappings? Or clear them? For now, keep. Frontend will show no headers to map to.
                    # else: header extraction failed, message already set by that stage.
                # === End of New/Modified Header Extraction and Template Logic ===
                            
            except Exception as e_save: 
                logger.error(f"Error saving/processing file {original_filename_for_vendor}: {e_save}", exc_info=True)
                results_entry["success"] = False
                results_entry["message"] = f"Error saving or processing file: {str(e_save)}"
                results_entry["file_type"] = "error_system"
            
            results.append(results_entry)
            log_message = (f"File: {results_entry.get('filename', 'N/A')} (Original: {original_filename_for_vendor}), "
                           f"Status: {'Success' if results_entry.get('success') else 'Failure'}, "
                           f"Type: {results_entry.get('file_type', 'unknown')}, Msg: {results_entry.get('message')}, "
                           f"Headers: {len(results_entry.get('headers',[]))}, Mappings: {len(results_entry.get('field_mappings',[]))}, "
                           f"SkipRows: {results_entry.get('skip_rows', 0)}")
            if results_entry.get("applied_template_name"):
                log_message += f", AppliedTemplate: {results_entry.get('applied_template_name')}"
            if "original_pdf_filename" in results_entry and results_entry["original_pdf_filename"] != results_entry["filename"]: # Log if different
                log_message += f", OriginalPDF: {results_entry['original_pdf_filename']}"

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
        suggestions = chatbot_service.get_mapping_suggestions(original_header, current_mapped_field, FIELD_DEFINITIONS)
        return jsonify(suggestions)
    except Exception as e:
        logger.error(f"Chatbot suggestion error: {e}", exc_info=True)
        return jsonify({"error": "Internal error generating suggestions."}), 500


# Helper function to convert NaT/NaN to None and Timestamps to ISO strings for JSON serialization
def sanitize_data_for_json(item):
    if isinstance(item, list):
        return [sanitize_data_for_json(x) for x in item]
    if isinstance(item, dict):
        return {k: sanitize_data_for_json(v) for k, v in item.items()}
    # Check for pd.NaT (Not a Time)
    if item is pd.NaT:
        return None
    # Convert pd.Timestamp to ISO format string
    if isinstance(item, pd.Timestamp):
        # Check if the timestamp is NaT before attempting isoformat
        if pd.isna(item):
            return None
        return item.isoformat()
    # Handle float NaN (often from numpy.nan)
    if isinstance(item, float) and pd.isna(item):
        return None
    return item

@app.route('/process_file_data', methods=['POST'])
def process_file_data_route():
    logger.info("Received request for /process_file_data")
    data = request.get_json()
    if not data:
        logger.warning("/process_file_data: No data provided in request.")
        return jsonify({"error": "No data provided"}), 400

    # Log the entire received payload for debugging
    logger.debug(f"/process_file_data: Full data received: {json.dumps(data)}")

    file_identifier = data.get('file_identifier')
    finalized_mappings = data.get('finalized_mappings')
    file_type = data.get('file_type')
    # Get skip_rows as string first, default to '0'
    skip_rows_str = str(data.get('skip_rows', '0')) # Ensure it's a string

    logger.info(f"/process_file_data: Parsed - ID: '{file_identifier}', FileType: '{file_type}', Mappings Count: {len(finalized_mappings) if finalized_mappings else 0}, SkipRows Str: '{skip_rows_str}'")
    
    try:
        skip_rows = int(skip_rows_str)
        if skip_rows < 0: 
            logger.warning(f"/process_file_data: Negative skip_rows '{skip_rows_str}' for '{file_identifier}', defaulting to 0.")
            skip_rows = 0
    except ValueError:
        logger.warning(f"/process_file_data: Invalid skip_rows value '{skip_rows_str}' for '{file_identifier}', defaulting to 0.")
        skip_rows = 0
    logger.info(f"/process_file_data: Final skip_rows value for '{file_identifier}': {skip_rows}")

    if not file_identifier:
        logger.warning("/process_file_data: Missing 'file_identifier'.")
        return jsonify({"error": "Missing required field: file_identifier"}), 400
    if finalized_mappings is None: # Check for None specifically, allow empty list
        logger.warning(f"/process_file_data: 'finalized_mappings' is missing for '{file_identifier}'. Proceeding with empty mappings.")
        finalized_mappings = [] 
    if not file_type:
        logger.warning("/process_file_data: Missing 'file_type'.")
        return jsonify({"error": "Missing required field: file_type"}), 400

    file_path_on_disk = os.path.join(app.config['UPLOAD_FOLDER'], file_identifier)
    if not os.path.exists(file_path_on_disk):
        if not os.path.exists(file_identifier): # Check if file_identifier itself is a full path
            logger.error(f"/process_file_data: File not found at UPLOAD_FOLDER path '{file_path_on_disk}' AND as direct path '{file_identifier}'.")
            return jsonify({"error": f"File not found: {file_identifier}"}), 404
        file_path_on_disk = file_identifier
        logger.info(f"/process_file_data: File identifier '{file_identifier}' was a full path. Using it directly: '{file_path_on_disk}'")

    logger.info(f"/process_file_data: Starting data extraction for: '{file_path_on_disk}', type: '{file_type}', skip_rows: {skip_rows}")
    try:
        if file_type == "PDF":
            logger.info(f"/process_file_data: PDF processing for '{file_identifier}'. Checking cache.")
            raw_pdf_content_for_extraction = TEMP_PDF_DATA_FOR_EXTRACTION.pop(file_identifier, None)
            if raw_pdf_content_for_extraction is None:
                logger.warning(f"/process_file_data: PDF data for '{file_identifier}' not in cache. Attempting re-fetch.")
                pdf_context_fallback = extract_headers_from_pdf_tables(file_path_on_disk)
                if isinstance(pdf_context_fallback, dict) and not pdf_context_fallback.get("error"):
                    raw_pdf_content_for_extraction = {
                        'headers': pdf_context_fallback.get('headers'),
                        'data_rows': pdf_context_fallback.get('data_rows')
                    }
                    logger.info(f"/process_file_data: Successfully re-fetched PDF context for '{file_identifier}'. Headers: {len(raw_pdf_content_for_extraction['headers']) if raw_pdf_content_for_extraction.get('headers') else 'None'}, Rows: {len(raw_pdf_content_for_extraction['data_rows']) if raw_pdf_content_for_extraction.get('data_rows') else 'None'}")
                else:
                    error_msg_detail = pdf_context_fallback.get('error', 'Unknown error during fallback') if isinstance(pdf_context_fallback, dict) else 'Type error in fallback result'
                    error_msg = f"PDF data for {file_identifier} not found in cache and could not be re-fetched. Fallback error: {error_msg_detail}."
                    logger.error(f"/process_file_data: {error_msg}")
                    return jsonify({"error": error_msg}), 400
            else:
                logger.info(f"/process_file_data: Found PDF data for '{file_identifier}' in cache. Headers: {len(raw_pdf_content_for_extraction['headers']) if raw_pdf_content_for_extraction.get('headers') else 'None'}, Rows: {len(raw_pdf_content_for_extraction['data_rows']) if raw_pdf_content_for_extraction.get('data_rows') else 'None'}")

            extracted_data_list_or_error = extract_data(
                file_path_on_disk,
                file_type,
                finalized_mappings,
                raw_pdf_table_content=raw_pdf_content_for_extraction
            )
        else: # For CSV/Excel
            logger.info(f"/process_file_data: CSV/Excel processing for '{file_identifier}'.")
            extracted_data_list_or_error = extract_data(
                file_path_on_disk,
                file_type,
                finalized_mappings,
                skip_rows=skip_rows
            )

        if isinstance(extracted_data_list_or_error, dict) and "error" in extracted_data_list_or_error:
            logger.error(f"/process_file_data: Data extraction error for '{file_path_on_disk}': {extracted_data_list_or_error['error']}")
            return jsonify(extracted_data_list_or_error), 400
        
        num_records = len(extracted_data_list_or_error) if isinstance(extracted_data_list_or_error, list) else 0
        logger.info(f"/process_file_data: Successfully processed '{file_path_on_disk}'. Extracted {num_records} records.") # Corrected f-string
        
        # Sanitize data before jsonify
        sanitized_data = sanitize_data_for_json(extracted_data_list_or_error)
        
        # Return the actual data and a success message
        return jsonify({'data': sanitized_data, 'message': f'Successfully processed {num_records} records from {file_identifier}.'})

    except Exception as e:
        logger.error(f"/process_file_data: Unexpected critical error during file processing for '{file_path_on_disk}': {e}", exc_info=True)
        return jsonify({"error": "Internal server error processing file. Please check server logs."}), 500

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
    logger.info("Received request for /save_template")
    data = request.get_json()
    if not data:
        logger.warning("/save_template: No data provided in request.")
        return jsonify({"error": "No data provided"}), 400
    
    logger.info(f"/save_template: Data received: {json.dumps(data)}")

    original_template_name = data.get('template_name', '').strip()
    field_mappings = data.get('field_mappings')
    # Get skip_rows as string first for robust parsing, default to '0'
    skip_rows_str = str(data.get('skip_rows', '0')) # Ensure it's a string for consistent handling
    overwrite = data.get('overwrite', False)

    logger.info(f"/save_template: Parsed parameters - Name: '{original_template_name}', Mappings Count: {len(field_mappings) if field_mappings else 0}, SkipRows Str: '{skip_rows_str}', Overwrite: {overwrite}")

    if not original_template_name:
        logger.warning("/save_template: Template name is required but was empty.")
        return jsonify({"error": "Template name is required."}), 400

    if not field_mappings or not isinstance(field_mappings, list) or len(field_mappings) == 0:
        logger.warning("/save_template: Field mappings are required and cannot be empty.")
        return jsonify({"error": "Field mappings are required and cannot be empty."}), 400
    
    try:
        skip_rows = int(skip_rows_str)
        if skip_rows < 0: 
            logger.warning(f"/save_template: Negative skip_rows '{skip_rows_str}' received, defaulting to 0.")
            skip_rows = 0
    except ValueError:
        logger.warning(f"/save_template: Invalid skip_rows value '{skip_rows_str}', defaulting to 0.")
        skip_rows = 0
    
    logger.info(f"/save_template: Final skip_rows value: {skip_rows}")


    sanitized_name_part = "".join(c if c.isalnum() or c in ('_', '-') else '' for c in original_template_name)
    if not sanitized_name_part:
        logger.warning(f"/save_template: Template name '{original_template_name}' sanitized to empty. Not saving.")
        return jsonify({"error": "Invalid template name after sanitization. Please provide a more descriptive name."}), 400

    safe_target_filename = f"{sanitized_name_part}.json"
    target_file_path = os.path.join(TEMPLATES_DIR, safe_target_filename)
    logger.info(f"/save_template: Target filename: '{safe_target_filename}', Full path: '{target_file_path}'")

    # Check 1: Exact Original Name Match in a *Different* File
    if os.path.exists(TEMPLATES_DIR):
        for existing_s_filename in os.listdir(TEMPLATES_DIR):
            if not existing_s_filename.endswith(".json") or existing_s_filename == safe_target_filename:
                continue # Skip self or non-json files
            try:
                with open(os.path.join(TEMPLATES_DIR, existing_s_filename), 'r', encoding='utf-8') as f:
                    existing_template_data = json.load(f)
                if existing_template_data.get('template_name') == original_template_name:
                    logger.warning(f"/save_template: Name conflict. Template name '{original_template_name}' already exists in '{existing_s_filename}'.")
                    return jsonify({
                        'status': 'error', 'error_type': 'NAME_ALREADY_EXISTS_IN_OTHER_FILE',
                        'message': f"A template with the name '{original_template_name}' already exists (saved as '{existing_s_filename}'). Please choose a unique name.",
                        'conflicting_filename': existing_s_filename
                    }), 409 # HTTP 409 Conflict
            except (IOError, json.JSONDecodeError) as e:
                logger.error(f"/save_template: Error reading/parsing '{existing_s_filename}' during name conflict check: {e}")
                # Optionally, decide if this error should halt the process or just be logged
                # For now, it logs and continues, meaning a potential conflict might be missed if a file is unreadable

    filename_exists = os.path.exists(target_file_path)
    logger.info(f"/save_template: Filename '{safe_target_filename}' exists: {filename_exists}, Overwrite flag: {overwrite}")

    if filename_exists and not overwrite:
        existing_internal_name = "N/A"
        try:
            with open(target_file_path, 'r', encoding='utf-8') as f:
                loaded_content = json.load(f)
            existing_internal_name = loaded_content.get('template_name', 'N/A')
            logger.info(f"/save_template: Filename clash. Existing template '{safe_target_filename}' has internal name '{existing_internal_name}'. Prompting for overwrite.")
        except (IOError, json.JSONDecodeError):
            logger.error(f"/save_template: Could not read existing template {target_file_path} to get its name during conflict check.")
        
        return jsonify({
            'status': 'conflict', 'error_type': 'FILENAME_CLASH',
            'message': f"A template file that would be named '{safe_target_filename}' already exists (it currently stores a template named '{existing_internal_name}'). Do you want to overwrite it?",
            'filename': safe_target_filename, 'existing_template_name': existing_internal_name
        }), 409

    # Proceed to save/overwrite if (filename_exists and overwrite) or (not filename_exists)
    if (filename_exists and overwrite) or (not filename_exists):
        template_data = {
            "template_name": original_template_name,
            "filename": safe_target_filename, 
            "creation_timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "field_mappings": field_mappings,
            "skip_rows": skip_rows 
        }
        try:
            with open(target_file_path, 'w', encoding='utf-8') as f:
                json.dump(template_data, f, indent=4)
            logger.info(f"/save_template: Successfully saved template '{original_template_name}' to '{safe_target_filename}'.")
            return jsonify({"status": "success", "message": f"Template '{original_template_name}' saved as '{safe_target_filename}'.", "filename": safe_target_filename, "template_name": original_template_name}), 200
        except IOError as e:
            logger.error(f"/save_template: Error writing template file '{target_file_path}': {e}", exc_info=True)
            return jsonify({"error": f"Could not save template to file: {str(e)}"}), 500
        except Exception as e_save: # Catch any other unexpected errors during save
            logger.error(f"/save_template: Unexpected error saving template '{target_file_path}': {e_save}", exc_info=True)
            return jsonify({"error": "An unexpected error occurred while saving the template."}), 500
    
    # Fallback return for the route if no other condition led to a response.
    # This should ideally not be reached if logic for conflicts and saving is sound.
    logger.error(f"/save_template: Reached end of function for '{original_template_name}' without a definitive action. This might indicate a logic flaw.")
    return jsonify({"error": "An unexpected internal server error occurred. Template processing was inconclusive."}), 500

@app.route('/download_processed_data', methods=['POST'])
def download_processed_data_route():
    logger.info("Received request for /download_processed_data")
    data_payload = request.get_json()
    if not data_payload:
        logger.warning("/download_processed_data: No data payload provided.")
        return jsonify({"error": "No data payload provided"}), 400

    file_identifier = data_payload.get('file_identifier')
    data_to_download = data_payload.get('data_to_download')

    logger.info(f"/download_processed_data: Preparing download for '{file_identifier}'. Data rows: {len(data_to_download) if isinstance(data_to_download, list) else 'N/A'}")

    if not file_identifier:
        logger.warning("/download_processed_data: Missing 'file_identifier'.")
        return jsonify({"error": "Missing file_identifier"}), 400
    
    if not data_to_download or not isinstance(data_to_download, list) or len(data_to_download) == 0:
        logger.warning(f"/download_processed_data: No data provided to download for '{file_identifier}'.")
        return jsonify({"error": "No data to download"}), 400

    try:
        # Create a string buffer to hold CSV data
        si = io.StringIO()
        cw = csv.writer(si)

        # Assuming data_to_download is a list of dictionaries
        # Write headers (keys from the first dictionary)
        if data_to_download:
            headers = data_to_download[0].keys()
            cw.writerow(headers)
            # Write data rows
            for row_dict in data_to_download:
                # Ensure all values are serializable (e.g., convert None to empty string for CSV)
                row_values = [str(row_dict.get(h, '')) for h in headers] 
                cw.writerow(row_values)
        
        output = io.BytesIO()
        output.write(si.getvalue().encode('utf-8'))
        output.seek(0)
        si.close()

        # Sanitize filename for download
        safe_filename_base = "".join(c if c.isalnum() or c in ('_', '-', '.') else '_' for c in file_identifier)
        download_filename = f"processed_{safe_filename_base}.csv"

        logger.info(f"/download_processed_data: Sending file '{download_filename}' for '{file_identifier}'.")
        return send_file(
            output,
            mimetype='text/csv',
            as_attachment=True,
            download_name=download_filename
        )

    except Exception as e:
        logger.error(f"/download_processed_data: Error generating CSV for '{file_identifier}': {e}", exc_info=True)
        return jsonify({"error": "Error generating CSV file. Please check server logs."}), 500

@app.route('/list_templates', methods=['GET'])
def list_templates_route():
    """List all templates available in the templates_storage directory."""
    logger.info("Retrieving template list.")
    templates = []
    
    try:
        if os.path.exists(TEMPLATES_DIR):
            for filename in os.listdir(TEMPLATES_DIR):
                if not filename.endswith('.json'):
                    continue
                    
                try:
                    filepath = os.path.join(TEMPLATES_DIR, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        template_data = json.load(f)
                        
                    templates.append({
                        'filename': filename,
                        'template_name': template_data.get('template_name', filename),
                        'creation_timestamp': template_data.get('creation_timestamp', 'Unknown')
                    })
                except (IOError, json.JSONDecodeError) as e:
                    logger.error(f"Error reading template '{filename}': {e}")
                    
            logger.info(f"Successfully listed {len(templates)} templates.")
            return jsonify(templates)
        else:
            logger.warning(f"Templates directory does not exist: {TEMPLATES_DIR}")
            return jsonify([])
            
    except Exception as e:
        logger.error(f"Error listing templates: {e}", exc_info=True)
        return jsonify({"error": "Failed to list templates due to a server error."}), 500

@app.route('/get_template_details/<path:template_filename>', methods=['GET'])
def get_template_details_route(template_filename):
    """Get detailed information for a specific template by its filename."""
    logger.info(f"Getting details for template: {template_filename}")
    
    try:
        template_path = os.path.join(TEMPLATES_DIR, template_filename)
        if not os.path.exists(template_path):
            logger.warning(f"Template not found: {template_filename}")
            return jsonify({"error": f"Template '{template_filename}' not found."}), 404
            
        with open(template_path, 'r', encoding='utf-8') as f:
            template_data = json.load(f)
            
        logger.info(f"Successfully retrieved details for template: {template_filename}")
        return jsonify(template_data)
        
    except (IOError, json.JSONDecodeError) as e:
        logger.error(f"Error reading template '{template_filename}': {e}", exc_info=True)
        return jsonify({"error": f"Error reading template: {str(e)}"}), 500
    except Exception as e:
        logger.error(f"Unexpected error getting template details for '{template_filename}': {e}", exc_info=True)
        return jsonify({"error": "An unexpected error occurred while retrieving template details."}), 500

@app.route('/reprocess_file', methods=['POST'])
def reprocess_file_route():
    """Process a file with a new skip rows value and return updated headers and mappings"""
    logger.info("Received request for /reprocess_file")
    try:
        # First log the raw request data for debugging
        raw_data = request.get_data(as_text=True)
        logger.info(f"/reprocess_file: Raw request data: {raw_data}")
        
        data = request.get_json()
        logger.info(f"/reprocess_file: Parsed JSON data: {json.dumps(data) if data else 'None'}")
        
        if not data:
            logger.warning("/reprocess_file: No data provided in request.")
            return jsonify({"success": False, "message": "No data provided"}), 400
    except Exception as e:
        logger.error(f"/reprocess_file: Error parsing request data: {e}", exc_info=True)
        return jsonify({"success": False, "message": f"Error parsing request: {str(e)}"}), 400

    # Extract parameters from request
    file_identifier = data.get('file_identifier')
    file_type = data.get('file_type')
    skip_rows_str = str(data.get('skip_rows', '0'))

    logger.info(f"/reprocess_file: Processing - ID: '{file_identifier}', FileType: '{file_type}', SkipRows: '{skip_rows_str}'")
    
    # Validate input parameters
    try:
        skip_rows = int(skip_rows_str)
        if skip_rows < 0: 
            logger.warning(f"/reprocess_file: Negative skip_rows '{skip_rows_str}', defaulting to 0.")
            skip_rows = 0
    except ValueError:
        logger.warning(f"/reprocess_file: Invalid skip_rows value '{skip_rows_str}', defaulting to 0.")
        skip_rows = 0
    
    if not file_identifier:
        logger.warning("/reprocess_file: Missing 'file_identifier'.")
        return jsonify({"success": False, "message": "Missing required field: file_identifier"}), 400
    
    if not file_type:
        logger.warning("/reprocess_file: Missing 'file_type'.")
        return jsonify({"success": False, "message": "Missing required field: file_type"}), 400
    
    # Only allow reprocessing of certain file types
    if file_type not in ["CSV", "XLSX", "XLS"]:
        logger.error(f"/reprocess_file: Unsupported file type: {file_type}")
        return jsonify({"success": False, "message": f"Reprocessing not supported for file type: {file_type}"}), 400

    # Determine file path
    file_path_on_disk = os.path.join(app.config['UPLOAD_FOLDER'], file_identifier)
    if not os.path.exists(file_path_on_disk):
        if not os.path.exists(file_identifier): # Check if file_identifier itself is a full path
            logger.error(f"/reprocess_file: File not found at '{file_path_on_disk}' OR as direct path '{file_identifier}'.")
            return jsonify({"success": False, "message": f"File not found: {file_identifier}"}), 404
        file_path_on_disk = file_identifier
        logger.info(f"/reprocess_file: Using direct path: '{file_path_on_disk}'")

    try:
        # Extract headers again with the new skip_rows value
        logger.info(f"/reprocess_file: Extracting headers with skip_rows={skip_rows}")
        result = extract_headers(file_path_on_disk, file_type, skip_rows=skip_rows)
        logger.info(f"/reprocess_file: Headers extraction result type: {type(result)}, value: {result}")
        
        # Handle the case where result is a dictionary with an "error" key
        if isinstance(result, dict) and "error" in result:
            logger.error(f"/reprocess_file: Failed to extract headers: {result['error']}")
            return jsonify({"success": False, "message": f"Failed to extract headers: {result['error']}"}), 400
            
        # Handle the case where result is already a list of headers (the expected case)
        if isinstance(result, list):
            headers = result
        # Handle the case where result is a dict with headers key (shouldn't happen with current implementation)
        elif isinstance(result, dict) and "headers" in result:
            headers = result["headers"]
        else:
            # Handle unexpected return type
            logger.error(f"/reprocess_file: Unexpected result type: {type(result)}")
            return jsonify({"success": False, "message": f"Unexpected result from header extraction"}), 500
        
        # Generate field mappings with the new headers
        if headers:
            logger.info(f"/reprocess_file: Found {len(headers)} headers, generating field mappings")
            field_mappings = header_mapper.generate_mappings(headers, FIELD_DEFINITIONS)
            
            response_data = {
                "success": True,
                "message": f"Successfully reprocessed file with {skip_rows} rows skipped",
                "headers": headers,
                "field_mappings": field_mappings,
                "file_type": file_type,
                "filename": file_identifier
            }
            
            logger.info(f"/reprocess_file: Success for '{file_identifier}' with {len(headers)} headers")
            return jsonify(response_data)
        else:
            logger.warning(f"/reprocess_file: No headers found for '{file_identifier}' with skip_rows={skip_rows}")
            return jsonify({
                "success": False,
                "message": f"No headers found with {skip_rows} rows skipped. Try a different value."
            }), 400
            
    except Exception as e:
        logger.error(f"/reprocess_file: Unexpected error for '{file_identifier}': {e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"Error reprocessing file: {str(e)}"
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring and AWS App Runner."""
    try:
        # Return minimal success response to ensure quick health checks
        return jsonify({"status": "healthy"}), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

@app.route('/healthz', methods=['GET'])
def detailed_health_check():
    """Detailed health check endpoint for monitoring."""
    try:
        # Check if critical directories exist
        directories_ok = all([
            os.path.exists(app.config['UPLOAD_FOLDER']),
            os.path.exists(TEMPLATES_DIR),
            os.path.exists(LEARNED_PREFERENCES_DIR)
        ])
        
        # Check if field definitions were loaded successfully
        field_defs_ok = len(FIELD_DEFINITIONS) > 0
        
        # Optional: Check Azure OpenAI connection if it's configured
        azure_openai_status = "not_configured"
        if azure_openai_configured:
            try:
                test_result = test_azure_openai_connection()
                azure_openai_status = "ok" if test_result.get("success") else "error"
            except Exception:
                azure_openai_status = "error"
        
        # Overall health is good if directories and field definitions are OK
        health_ok = directories_ok and field_defs_ok
        
        return jsonify({
            "status": "healthy" if health_ok else "degraded",
            "timestamp": datetime.datetime.now().isoformat(),
            "checks": {
                "directories": "ok" if directories_ok else "error",
                "field_definitions": "ok" if field_defs_ok else "error",
                "azure_openai": azure_openai_status
            }
        }), 200 if health_ok else 503
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return jsonify({
            "status": "unhealthy",
            "timestamp": datetime.datetime.now().isoformat(),
            "error": str(e)
        }), 500

# --- Debug/test routes ---
@app.route('/test/list_templates', methods=['GET'])
def test_list_templates_route():
    """Debug route to view template information."""
    template_info = []
    
    if os.path.exists(TEMPLATES_DIR):
        for filename in os.listdir(TEMPLATES_DIR):
            file_path = os.path.join(TEMPLATES_DIR, filename)
            file_info = {
                'filename': filename,
                'path': file_path,
                'exists': os.path.exists(file_path),
                'is_file': os.path.isfile(file_path),
                'size': os.path.getsize(file_path) if os.path.exists(file_path) and os.path.isfile(file_path) else 'N/A',
            }
            
            # Try to read if it's a JSON file
            if filename.endswith('.json') and os.path.isfile(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        file_info['content'] = content
                        try:
                            file_info['parsed'] = json.loads(content)
                        except json.JSONDecodeError as e:
                            file_info['parse_error'] = str(e)
                except IOError as e:
                    file_info['read_error'] = str(e)
            
            template_info.append(file_info)
    else:
        return f"Templates directory '{TEMPLATES_DIR}' does not exist!"
    
    return jsonify({
        'templates_dir': TEMPLATES_DIR,
        'exists': os.path.exists(TEMPLATES_DIR),
        'is_dir': os.path.isdir(TEMPLATES_DIR) if os.path.exists(TEMPLATES_DIR) else False,
        'files': template_info
    })

@app.route('/debug', methods=['GET'])
def debug_info():
    """Debug endpoint to check environment variables and system information."""
    import sys
    import platform
    
    # Collect basic system and environment information
    debug_info = {
        "python_version": sys.version,
        "platform": platform.platform(),
        "environment_vars": {k: v for k, v in os.environ.items() if not k.lower().startswith(('azure', 'aws', 'secret', 'key', 'token', 'password'))},
        "app_config": {
            "UPLOAD_FOLDER_exists": os.path.exists(app.config['UPLOAD_FOLDER']),
            "TEMPLATES_DIR_exists": os.path.exists(TEMPLATES_DIR),
            "LEARNED_PREFERENCES_DIR_exists": os.path.exists(LEARNED_PREFERENCES_DIR),
            "workdir_contents": os.listdir('.') if os.path.exists('.') else [],
            "workdir_path": os.path.abspath('.'),
        },
        "field_definitions_loaded": len(FIELD_DEFINITIONS) > 0
    }
    
    return jsonify(debug_info)

# --- Debug/test routes ---
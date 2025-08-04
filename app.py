import sys
import os
import logging

# App Runner optimized Flask application

# Set up root logger for startup diagnostics
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
root_logger.addHandler(handler)

# Log import-time debugging information
root_logger.info("App starting up - Python version: %s", sys.version)
root_logger.info("Working directory: %s", os.getcwd())
root_logger.info("App Runner environment: %s", os.environ.get('AWS_EXECUTION_ENV', 'local'))

from flask import Flask, render_template, request, jsonify, send_from_directory, send_file, current_app
import os
import io
import logging
import json
import datetime
import pandas as pd
import re # Added import for regular expressions

# Direct import of magic module
import magic

from file_parser import extract_headers, extract_data, extract_headers_from_pdf_tables
from azure_openai_client import test_azure_openai_connection, azure_openai_configured
from data_validator import validate_uniqueness, validate_invoice_via_api # Import new validation functions
# from werkzeug.utils import secure_filename
import csv
from pdftocsv import extract_tables_from_file # Added for PDF to CSV conversion

# Import storage services
from storage_service import storage_service
from config.s3_config import S3Config

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

# Test Azure OpenAI connection in a non-blocking way
def test_azure_openai_async():
    """Test Azure OpenAI connection without blocking startup"""
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

# Only test Azure OpenAI if not in App Runner environment to avoid blocking startup
if os.environ.get('AWS_EXECUTION_ENV') != 'AWS_AppRunner_1':
    test_azure_openai_async()
else:
    logger.info("Running in App Runner - skipping Azure OpenAI connection test during startup")

# Log warning for external Invoice Validation API if URL is not set
if not app.config['INVOICE_VALIDATION_API_URL']:
    logger.warning("INVOICE_VALIDATION_API_URL is not set in environment variables. External invoice validation will be disabled.")

TEMP_PDF_DATA_FOR_EXTRACTION = {}

# Global dictionary to store extracted text data for all processed files
EXTRACTED_TEXT_CACHE = {}

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
    try:
        return render_template('index.html', field_definitions_json=json.dumps(FIELD_DEFINITIONS))
    except Exception as e:
        # Fallback for App Runner if templates fail
        return jsonify({
            "status": "app_running",
            "message": "Vendor Statements Processor is running",
            "health_check": "/health",
            "error": str(e) if e else None
        })

@app.route('/manage_templates')
def manage_templates_page():
    return render_template('manage_templates.html')



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
                
                # Also save to S3 if enabled (async backup)
                try:
                    s3_key = storage_service.save_file(file_path)
                    if s3_key:
                        logger.info(f"File {filename} also saved to S3 storage: {s3_key}")
                        results_entry["s3_key"] = s3_key
                        results_entry["storage_backend"] = storage_service.get_storage_info()['backend']
                except Exception as e_s3:
                    logger.warning(f"Failed to save {filename} to S3 (continuing with local): {e_s3}")
                    # Don't fail the upload if S3 save fails

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

                    # 1. Extract Template Name from original filename (Enhanced Logic)
                    template_name_from_file = ""
                    if original_filename_for_vendor:
                        name_without_extension = os.path.splitext(original_filename_for_vendor)[0]
                        # Split by the first occurrence of space, underscore, or hyphen
                        parts = re.split(r'[ _-]', name_without_extension, 1)
                        if parts: 
                            template_name_from_file = parts[0]
                            logger.info(f"Extracted template name '{template_name_from_file}' from filename '{original_filename_for_vendor}'")

                    # 2. Enhanced Template Search and Auto-Apply Logic
                    if template_name_from_file and os.path.exists(TEMPLATES_DIR):
                        logger.info(f"Searching for template matching: '{template_name_from_file}' from filename '{original_filename_for_vendor}'")
                        normalized_template_name = template_name_from_file.lower()
                        
                        # Get all template files and sort by specificity (longer names first for better matching)
                        template_files = [f for f in os.listdir(TEMPLATES_DIR) if f.endswith(".json")]
                        template_files.sort(key=lambda x: len(os.path.splitext(x)[0]), reverse=True)
                        
                        for template_file_in_storage in template_files:
                            template_base_name = os.path.splitext(template_file_in_storage)[0]
                            template_base_name_lower = template_base_name.lower()
                            
                            # Enhanced matching: exact match or starts with
                            is_exact_match = template_base_name_lower == normalized_template_name
                            is_prefix_match = template_base_name_lower.startswith(normalized_template_name + "-") or \
                                            normalized_template_name.startswith(template_base_name_lower)
                            
                            if is_exact_match or is_prefix_match:
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
                                        
                                        match_type = "exact" if is_exact_match else "prefix"
                                        logger.info(f"🎯 AUTO-APPLIED template '{template_file_in_storage}' ({match_type} match) for filename '{original_filename_for_vendor}'. Skip rows: {current_skip_rows_for_extraction}")
                                        break # Stop searching once a template is found
                                except Exception as e_tpl_load:
                                    logger.error(f"Error loading template {template_file_in_storage} for {template_name_from_file}: {e_tpl_load}")
                        
                        if not template_applied_data:
                            logger.info(f"No template found for '{template_name_from_file}'. Available templates: {[os.path.splitext(f)[0] for f in template_files]}")
                    else:
                        logger.info(f"No template name extracted from filename '{original_filename_for_vendor}' or templates directory not found")
                    
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

                    # 4. Generate and cache extracted text data
                    if results_entry["success"] and actual_headers_from_file:
                        try:
                            # Extract sample data for text generation
                            sample_data_rows = []
                            total_rows = 0
                            
                            if detected_type_name == "PDF":
                                # Use cached PDF data
                                if original_filename_for_vendor in TEMP_PDF_DATA_FOR_EXTRACTION:
                                    pdf_data = TEMP_PDF_DATA_FOR_EXTRACTION[original_filename_for_vendor]
                                    sample_data_rows = pdf_data.get('data_rows', [])
                                    total_rows = len(sample_data_rows)
                            else:
                                # Extract data for CSV/Excel files - create mappings for all headers to get all data
                                all_headers_mapping = [{'original_header': header, 'mapped_field': header} for header in actual_headers_from_file]
                                data_result = extract_data(effective_file_path_for_processing, detected_type_name, all_headers_mapping, skip_rows=current_skip_rows_for_extraction)
                                if isinstance(data_result, list):
                                    sample_data_rows = data_result
                                    total_rows = len(data_result)
                            
                            # Generate extracted text
                            extracted_text = generate_extracted_text(
                                filename=results_entry["filename"],
                                file_type=detected_type_name,
                                headers=actual_headers_from_file,
                                data_rows=sample_data_rows,
                                total_rows=total_rows
                            )
                            
                            # Cache the extracted text data (sanitized for JSON)
                            cache_data = {
                                "extracted_text": extracted_text,
                                "headers": actual_headers_from_file,
                                "sample_rows": sample_data_rows,  # All rows for full content view
                                "total_rows": total_rows,
                                "file_type": detected_type_name,
                                "parsing_info": f"Successfully parsed {detected_type_name} with {len(actual_headers_from_file)} headers and {total_rows} rows"
                            }
                            EXTRACTED_TEXT_CACHE[results_entry["filename"]] = sanitize_data_for_json(cache_data)
                            
                            logger.info(f"Generated and cached extracted text for {results_entry['filename']}")
                            
                        except Exception as e_text:
                            logger.error(f"Error generating extracted text for {results_entry['filename']}: {e_text}")
                            # Don't fail the entire process if text generation fails
                    
                    # 5. Determine Field Mappings (Template or Auto-generated), only if header extraction was successful
                    if results_entry["success"]: # Check if header extraction above was successful
                        if actual_headers_from_file: # If headers were found
                            if template_applied_data:
                                results_entry["field_mappings"] = template_applied_data.get("field_mappings", [])
                                # results_entry["skip_rows"] is already set from template
                                results_entry["message"] = f"🎯 Template '{results_entry['applied_template_name']}' auto-applied (matched first word '{template_name_from_file}') with {results_entry['skip_rows']} skip rows."
                                logger.info(f"Applied template mappings for '{original_filename_for_vendor}'.")
                            else: # No template applied, generate intelligent AI mappings
                                logger.info(f"No template found for '{template_name_from_file}'. Using Azure OpenAI for intelligent field mapping.")
                                mappings = header_mapper.generate_mappings(actual_headers_from_file, FIELD_DEFINITIONS)
                                results_entry["field_mappings"] = mappings
                                # results_entry["skip_rows"] remains default 0 if no template
                                
                                # Analyze mapping quality and provide informative message
                                high_confidence_count = sum(1 for m in mappings if m.get('confidence_score', 0) >= 80)
                                total_mappings = len([m for m in mappings if m.get('mapped_field') != 'N/A'])
                                
                                if high_confidence_count >= len(mappings) * 0.7:  # 70% or more high confidence
                                    results_entry["message"] = f"🤖 AI auto-mapped {high_confidence_count}/{len(mappings)} headers with high confidence."
                                elif total_mappings > 0:
                                    results_entry["message"] = f"🤖 AI mapped {total_mappings}/{len(mappings)} headers. Review and adjust as needed."
                                else:
                                    results_entry["message"] = f"🤖 AI analyzed {len(mappings)} headers. Manual mapping may be needed."
                                
                                logger.info(f"🤖 AI generated {len(mappings)} mappings for {original_filename_for_vendor}: {high_confidence_count} high-confidence, {total_mappings} total mapped.")
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
def generate_extracted_text(filename, file_type, headers, data_rows, total_rows):
    """Generate extracted text representation of file data"""
    text_lines = []
    text_lines.append(f"=== PARSED {file_type.upper()} CONTENT ===")
    text_lines.append(f"File: {filename}")
    text_lines.append(f"Headers Found: {len(headers)}")
    text_lines.append(f"Total Rows: {total_rows}")
    text_lines.append("")
    
    if headers:
        text_lines.append("HEADERS:")
        for i, header in enumerate(headers, 1):
            text_lines.append(f"  {i}. {header}")
        text_lines.append("")
        
        if data_rows:
            text_lines.append("ALL DATA:")
            for i, row in enumerate(data_rows, 1):
                text_lines.append(f"Row {i}:")
                if isinstance(row, dict):
                    for header in headers:
                        value = row.get(header, '')
                        text_lines.append(f"  {header}: {value}")
                else:
                    # Handle case where row is a list
                    for j, value in enumerate(row):
                        header = headers[j] if j < len(headers) else f"Column_{j}"
                        text_lines.append(f"  {header}: {value}")
                text_lines.append("")
    else:
        text_lines.append("No headers found in file.")
    
    return "\n".join(text_lines)

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
    """View the original raw file content (before any processing/conversion)"""
    try:
        upload_folder_abs = os.path.abspath(app.config['UPLOAD_FOLDER'])
        
        # Check if this is a converted file (ends with -converted.csv)
        if filename.endswith('-converted.csv'):
            # Try to find the original file (likely a PDF)
            base_name = filename.replace('-converted.csv', '')
            
            # Look for common original file extensions
            for ext in ['.pdf', '.PDF']:
                original_filename = base_name + ext
                original_path = os.path.join(upload_folder_abs, original_filename)
                if os.path.exists(original_path):
                    logger.info(f"Serving original file: {original_filename} instead of converted {filename}")
                    return send_from_directory(upload_folder_abs, original_filename, as_attachment=False)
            
            # If no original found, serve the converted file
            logger.warning(f"Original file not found for {filename}, serving converted file")
        
        # Serve the requested file directly
        logger.info(f"Serving file: {filename} from {upload_folder_abs}")
        return send_from_directory(upload_folder_abs, filename, as_attachment=False)
    except FileNotFoundError:
        logger.error(f"File not found: {filename} in {upload_folder_abs}", exc_info=True)
        return "File not found.", 404
    except Exception as e:
        logger.error(f"Error serving file {filename}: {e}", exc_info=True)
        return "Error serving file.", 500

@app.route('/view_raw_file/<path:filename>')
def view_raw_file(filename):
    """View raw file content in a formatted way, showing original content before any processing"""
    try:
        upload_folder_abs = os.path.abspath(app.config['UPLOAD_FOLDER'])
        
        # Determine the original filename
        original_filename = filename
        if filename.endswith('-converted.csv'):
            # Try to find the original file (likely a PDF)
            base_name = filename.replace('-converted.csv', '')
            for ext in ['.pdf', '.PDF']:
                potential_original = base_name + ext
                if os.path.exists(os.path.join(upload_folder_abs, potential_original)):
                    original_filename = potential_original
                    break
        
        file_path = os.path.join(upload_folder_abs, original_filename)
        if not os.path.exists(file_path):
            return jsonify({"error": f"Original file not found: {original_filename}"}), 404
        
        # Get file info
        file_stats = os.stat(file_path)
        file_size = file_stats.st_size
        _, file_extension = os.path.splitext(original_filename)
        file_extension = file_extension.lower()
        
        raw_content = {
            "filename": original_filename,
            "display_filename": filename,  # The filename shown in UI
            "file_size": file_size,
            "file_type": file_extension.replace('.', '').upper(),
            "content": "",
            "content_type": "text",
            "message": ""
        }
        
        # Handle different file types
        if file_extension == '.pdf':
            raw_content["content"] = f"PDF File: {original_filename}\nSize: {file_size} bytes\n\nThis is a PDF file. To view the raw content, click 'View Raw File' to download or open in browser."
            raw_content["content_type"] = "pdf_info"
            raw_content["message"] = "PDF files cannot be displayed as text. Use 'Preview File' to see extracted data."
            
        elif file_extension in ['.csv']:
            # Read first 100 lines of CSV to show raw content
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = []
                    for i, line in enumerate(f):
                        if i >= 100:  # Limit to first 100 lines
                            lines.append("... (file truncated for display)")
                            break
                        lines.append(line.rstrip())
                    
                    raw_content["content"] = '\n'.join(lines)
                    raw_content["content_type"] = "csv_text"
                    raw_content["message"] = f"Showing first {min(100, len(lines))} lines of CSV file"
                    
            except Exception as e:
                raw_content["content"] = f"Error reading CSV file: {str(e)}"
                raw_content["content_type"] = "error"
                
        elif file_extension in ['.xlsx', '.xls']:
            raw_content["content"] = f"Excel File: {original_filename}\nSize: {file_size} bytes\n\nThis is an Excel file. Raw binary content cannot be displayed as text.\nUse 'Preview File' to see the extracted data."
            raw_content["content_type"] = "excel_info"
            raw_content["message"] = "Excel files cannot be displayed as text. Use 'Preview File' to see extracted data."
            
        else:
            # Try to read as text file
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read(10000)  # Limit to first 10KB
                    if len(content) == 10000:
                        content += "\n... (file truncated for display)"
                    raw_content["content"] = content
                    raw_content["content_type"] = "text"
                    raw_content["message"] = "Raw file content"
            except UnicodeDecodeError:
                raw_content["content"] = f"Binary File: {original_filename}\nSize: {file_size} bytes\n\nThis appears to be a binary file that cannot be displayed as text."
                raw_content["content_type"] = "binary_info"
                raw_content["message"] = "Binary files cannot be displayed as text."
        
        return jsonify(sanitize_data_for_json(raw_content))
        
    except Exception as e:
        logger.error(f"Error viewing raw file {filename}: {e}", exc_info=True)
        return jsonify({"error": f"Error viewing raw file: {str(e)}"}), 500

@app.route('/save_template', methods=['POST'])
def save_template_route():
    """Save a template using the storage service (S3 or local)"""
    logger.info("Received request for /save_template")
    data = request.get_json()
    if not data:
        logger.warning("/save_template: No data provided in request.")
        return jsonify({"error": "No data provided"}), 400
    
    logger.info(f"/save_template: Data received: {json.dumps(data)}")

    original_template_name = data.get('template_name', '').strip()
    field_mappings = data.get('field_mappings')
    skip_rows_str = str(data.get('skip_rows', '0'))
    overwrite = data.get('overwrite', False)

    logger.info(f"/save_template: Parsed parameters - Name: '{original_template_name}', Mappings Count: {len(field_mappings) if field_mappings else 0}, SkipRows Str: '{skip_rows_str}', Overwrite: {overwrite}")

    # Validation
    if not original_template_name:
        logger.warning("/save_template: Template name is required but was empty.")
        return jsonify({"error": "Template name is required."}), 400

    if not field_mappings or not isinstance(field_mappings, list) or len(field_mappings) == 0:
        logger.warning("/save_template: Field mappings are required and cannot be empty.")
        return jsonify({"error": "Field mappings are required and cannot be empty."}), 400
    
    # Parse skip_rows
    try:
        skip_rows = int(skip_rows_str)
        if skip_rows < 0: 
            logger.warning(f"/save_template: Negative skip_rows '{skip_rows_str}' received, defaulting to 0.")
            skip_rows = 0
    except ValueError:
        logger.warning(f"/save_template: Invalid skip_rows value '{skip_rows_str}', defaulting to 0.")
        skip_rows = 0
    
    logger.info(f"/save_template: Final skip_rows value: {skip_rows}")

    # Sanitize template name for storage
    sanitized_name = "".join(c if c.isalnum() or c in ('_', '-') else '' for c in original_template_name)
    if not sanitized_name:
        logger.warning(f"/save_template: Template name '{original_template_name}' sanitized to empty. Not saving.")
        return jsonify({"error": "Invalid template name after sanitization. Please provide a more descriptive name."}), 400

    # Check for existing template with same name
    if not overwrite:
        existing_templates = storage_service.list_templates()
        for template_name in existing_templates:
            existing_template = storage_service.load_template(template_name)
            if existing_template and existing_template.get('template_name') == original_template_name:
                logger.warning(f"/save_template: Template with name '{original_template_name}' already exists.")
                return jsonify({
                    'status': 'conflict', 
                    'error_type': 'NAME_ALREADY_EXISTS',
                    'message': f"A template with the name '{original_template_name}' already exists. Do you want to overwrite it?",
                    'existing_template_name': original_template_name
                }), 409

        # Check if sanitized name exists as a template
        if storage_service.template_exists(sanitized_name):
            existing_template = storage_service.load_template(sanitized_name)
            existing_name = existing_template.get('template_name', sanitized_name) if existing_template else sanitized_name
            logger.warning(f"/save_template: Template file '{sanitized_name}' already exists with name '{existing_name}'.")
            return jsonify({
                'status': 'conflict',
                'error_type': 'FILENAME_CLASH', 
                'message': f"A template file '{sanitized_name}' already exists (contains template '{existing_name}'). Do you want to overwrite it?",
                'filename': f"{sanitized_name}.json",
                'existing_template_name': existing_name
            }), 409

    # Create template data
    template_data = {
        "template_name": original_template_name,
        "filename": f"{sanitized_name}.json",
        "creation_timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "field_mappings": field_mappings,
        "skip_rows": skip_rows,
        "storage_backend": storage_service.get_storage_info()['backend']
    }

    # Save template using storage service
    try:
        success = storage_service.save_template(sanitized_name, template_data)
        if success:
            logger.info(f"/save_template: Successfully saved template '{original_template_name}' to {storage_service.get_storage_info()['backend']} storage.")
            return jsonify({
                "status": "success", 
                "message": f"Template '{original_template_name}' saved successfully to {storage_service.get_storage_info()['backend']} storage.", 
                "filename": f"{sanitized_name}.json", 
                "template_name": original_template_name,
                "storage_backend": storage_service.get_storage_info()['backend']
            }), 200
        else:
            logger.error(f"/save_template: Failed to save template '{original_template_name}' to storage.")
            return jsonify({"error": "Failed to save template to storage."}), 500
            
    except Exception as e:
        logger.error(f"/save_template: Unexpected error saving template '{original_template_name}': {e}", exc_info=True)
        return jsonify({"error": f"An unexpected error occurred while saving the template: {str(e)}"}), 500

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
        # Define the specific column headers as requested
        target_columns = [
            "Case Number",
            "Customer Code", 
            "Customer Name",
            "Facility Name",
            "Facility Code",
            "Account Number",
            "Supplier Name",
            "Supplier Code", 
            "Invoice Number",
            "Invoice Date",
            "Invoice Amount"
        ]
        
        # Create mapping from field definitions to target columns
        field_mapping = {
            "CaseNumber": "Case Number",
            "CustomerCode": "Customer Code",
            "CustomerName": "Customer Name", 
            "FacilityName": "Facility Name",
            "FacilityCode": "Facility Code",
            "AccountNumber": "Account Number",
            "SupplierName": "Supplier Name",
            "VendorName": "Supplier Name",  # Fallback mapping
            "SupplierCode": "Supplier Code",
            "InvoiceNumber": "Invoice Number",
            "InvoiceID": "Invoice Number",  # Fallback mapping
            "InvoiceDate": "Invoice Date",
            "InvoiceAmount": "Invoice Amount",
            "TotalAmount": "Invoice Amount"  # Fallback mapping
        }
        
        # Create DataFrame with target columns
        processed_data = []
        
        for row_dict in data_to_download:
            processed_row = {}
            
            # Initialize all target columns with empty values
            for col in target_columns:
                processed_row[col] = ""
            
            # Map data from source fields to target columns
            for source_field, target_column in field_mapping.items():
                if source_field in row_dict and target_column in target_columns:
                    value = row_dict[source_field]
                    # Convert None to empty string and ensure string format
                    processed_row[target_column] = str(value) if value is not None else ""
            
            processed_data.append(processed_row)
        
        # Create DataFrame with the specific column order
        df = pd.DataFrame(processed_data, columns=target_columns)
        
        # Create Excel file in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Processed Data', index=False)
        
        output.seek(0)

        # Sanitize filename for download
        safe_filename_base = "".join(c if c.isalnum() or c in ('_', '-', '.') else '_' for c in file_identifier)
        download_filename = f"processed_{safe_filename_base}.xlsx"

        logger.info(f"/download_processed_data: Sending Excel file '{download_filename}' for '{file_identifier}' with {len(processed_data)} rows.")
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=download_filename
        )

    except Exception as e:
        logger.error(f"/download_processed_data: Error generating Excel file for '{file_identifier}': {e}", exc_info=True)
        return jsonify({"error": "Error generating Excel file. Please check server logs."}), 500

@app.route('/list_templates', methods=['GET'])
def list_templates_route():
    """List all templates available in storage."""
    logger.info("Retrieving template list from storage.")
    templates = []
    
    try:
        template_names = storage_service.list_templates()
        
        for template_name in template_names:
            try:
                template_data = storage_service.load_template(template_name)
                if template_data:
                    templates.append({
                        'filename': f"{template_name}.json",
                        'file_id': f"{template_name}.json",
                        'template_name': template_data.get('template_name', template_name),
                        'display_name': template_data.get('template_name', template_name),
                        'creation_timestamp': template_data.get('creation_timestamp', 'Unknown'),
                        'storage_backend': storage_service.get_storage_info()['backend']
                    })
                else:
                    logger.warning(f"Could not load template data for '{template_name}'")
                    
            except Exception as e:
                logger.error(f"Error reading template '{template_name}': {e}")
                    
        logger.info(f"Successfully listed {len(templates)} templates from {storage_service.get_storage_info()['backend']} storage.")
        return jsonify({"templates": templates})
            
    except Exception as e:
        logger.error(f"Error listing templates: {e}", exc_info=True)
        return jsonify({"error": "Failed to list templates due to a server error."}), 500

@app.route('/get_template_details/<path:template_filename>', methods=['GET'])
def get_template_details_route(template_filename):
    """Get detailed information for a specific template by its filename."""
    logger.info(f"Getting details for template: {template_filename}")
    
    try:
        # Extract template name from filename (remove .json extension)
        template_name = template_filename
        if template_name.endswith('.json'):
            template_name = template_name[:-5]
        
        template_data = storage_service.load_template(template_name)
        if not template_data:
            logger.warning(f"Template not found: {template_filename}")
            return jsonify({"error": f"Template '{template_filename}' not found."}), 404
            
        logger.info(f"Successfully retrieved details for template: {template_filename} from {storage_service.get_storage_info()['backend']} storage")
        return jsonify(template_data)
        
    except Exception as e:
        logger.error(f"Unexpected error getting template details for '{template_filename}': {e}", exc_info=True)
        return jsonify({"error": "An unexpected error occurred while retrieving template details."}), 500

@app.route('/apply_template', methods=['POST'])
def apply_template_route():
    """Apply a template to a specific uploaded file."""
    logger.info("Received request for /apply_template")
    
    data = request.get_json()
    if not data:
        logger.warning("apply_template_route: No data provided.")
        return jsonify({"error": "No data provided"}), 400
    
    template_filename = data.get('template_filename')
    file_identifier = data.get('file_identifier')
    file_type = data.get('file_type')
    
    if not template_filename:
        logger.warning("apply_template_route: Missing template_filename.")
        return jsonify({"error": "Missing required field: template_filename"}), 400
    
    if not file_identifier:
        logger.warning("apply_template_route: Missing file_identifier.")
        return jsonify({"error": "Missing required field: file_identifier"}), 400
    
    if not file_type:
        logger.warning("apply_template_route: Missing file_type.")
        return jsonify({"error": "Missing required field: file_type"}), 400
    
    # Load template using storage service
    template_name = template_filename
    if template_name.endswith('.json'):
        template_name = template_name[:-5]
    
    template_data = storage_service.load_template(template_name)
    if not template_data:
        logger.warning(f"apply_template_route: Template not found: {template_filename}")
        return jsonify({"error": f"Template file not found: {template_filename}"}), 404
    
    try:
        
        # Validate template structure
        if "field_mappings" not in template_data:
            logger.error(f"apply_template_route: Invalid template structure in {template_filename}")
            return jsonify({"error": "Invalid template: missing field_mappings"}), 400
        
        skip_rows = template_data.get("skip_rows", 0)
        
        # Check if file exists
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_identifier)
        if not os.path.exists(file_path):
            logger.error(f"apply_template_route: File not found: {file_path}")
            return jsonify({"error": f"File not found: {file_identifier}"}), 404
        
        # Re-extract headers with the template's skip_rows
        logger.info(f"apply_template_route: Re-extracting headers for {file_identifier} with skip_rows={skip_rows}")
        
        if file_type == "PDF":
            # For PDF files, use the cached data or re-extract
            pdf_data = TEMP_PDF_DATA_FOR_EXTRACTION.get(file_identifier)
            if pdf_data:
                headers = pdf_data.get('headers', [])
            else:
                # Re-extract from PDF
                headers_result = extract_headers_from_pdf_tables(file_path)
                if isinstance(headers_result, dict) and "error" not in headers_result:
                    headers = headers_result.get("headers", [])
                    # Cache the result
                    TEMP_PDF_DATA_FOR_EXTRACTION[file_identifier] = headers_result
                else:
                    logger.error(f"apply_template_route: Error extracting headers from PDF {file_identifier}")
                    return jsonify({"error": "Error extracting headers from PDF"}), 400
        else:
            # For CSV/XLS/XLSX files
            headers_result = extract_headers(file_path, file_type, skip_rows=skip_rows)
            if isinstance(headers_result, dict) and "error" in headers_result:
                logger.error(f"apply_template_route: Error extracting headers: {headers_result['error']}")
                return jsonify({"error": f"Error extracting headers: {headers_result['error']}"}), 400
            headers = headers_result if isinstance(headers_result, list) else []
        
        if not headers:
            logger.warning(f"apply_template_route: No headers found in {file_identifier} with skip_rows={skip_rows}")
            return jsonify({"error": f"No headers found with skip_rows={skip_rows}"}), 400
        
        # Apply template mappings
        template_mappings = template_data.get("field_mappings", [])
        applied_mappings = []
        
        for header in headers:
            # Look for this header in the template mappings
            template_mapping = None
            for mapping in template_mappings:
                if mapping.get("original_header") == header:
                    template_mapping = mapping
                    break
            
            if template_mapping:
                applied_mappings.append({
                    "original_header": header,
                    "mapped_field": template_mapping.get("mapped_field", ""),
                    "confidence": 1.0  # Template mappings have high confidence
                })
            else:
                # Use auto-mapping for headers not in template
                auto_mapping = header_mapper.generate_mappings([header], FIELD_DEFINITIONS)
                if auto_mapping:
                    applied_mappings.append(auto_mapping[0])
                else:
                    applied_mappings.append({
                        "original_header": header,
                        "mapped_field": "",
                        "confidence": 0.0
                    })
        
        response_data = {
            "success": True,
            "message": f"Template '{template_data.get('template_name', template_filename)}' applied successfully",
            "template_name": template_data.get("template_name", template_filename),
            "template_filename": template_filename,
            "skip_rows": skip_rows,
            "headers": headers,
            "field_mappings": applied_mappings,
            "file_identifier": file_identifier,
            "file_type": file_type
        }
        
        logger.info(f"apply_template_route: Successfully applied template {template_filename} to {file_identifier}")
        return jsonify(response_data)
    
    except json.JSONDecodeError as e:
        logger.error(f"apply_template_route: JSON decode error for {template_filename}: {e}")
        return jsonify({"error": f"Invalid JSON in template file: {template_filename}"}), 400
    except Exception as e:
        logger.error(f"apply_template_route: Error applying template {template_filename}: {e}", exc_info=True)
        return jsonify({"error": f"Error applying template: {str(e)}"}), 500

@app.route('/delete_template/<path:template_filename>', methods=['DELETE'])
def delete_template_route(template_filename):
    """Delete a specific template file using storage service."""
    logger.info(f"Received request to delete template: {template_filename}")
    
    if not template_filename:
        logger.warning("delete_template_route: No template filename provided.")
        return jsonify({"error": "Template filename is required."}), 400
    
    # Extract template name from filename (remove .json extension)
    template_name = template_filename
    if template_name.endswith('.json'):
        template_name = template_name[:-5]
    
    # Check if template exists
    if not storage_service.template_exists(template_name):
        logger.warning(f"delete_template_route: Template not found: {template_filename}")
        return jsonify({"error": f"Template file not found: {template_filename}"}), 404
    
    try:
        success = storage_service.delete_template(template_name)
        if success:
            logger.info(f"delete_template_route: Successfully deleted template: {template_filename} from {storage_service.get_storage_info()['backend']} storage")
            return jsonify({
                "message": f"Template '{template_filename}' deleted successfully from {storage_service.get_storage_info()['backend']} storage.",
                "storage_backend": storage_service.get_storage_info()['backend']
            })
        else:
            logger.error(f"delete_template_route: Failed to delete template: {template_filename}")
            return jsonify({"error": f"Failed to delete template: {template_filename}"}), 500
    
    except Exception as e:
        logger.error(f"delete_template_route: Error deleting template {template_filename}: {e}", exc_info=True)
        return jsonify({"error": f"Error deleting template: {str(e)}"}), 500

@app.route('/field_definitions', methods=['GET'])
def field_definitions_route():
    """Get field definitions for template creation."""
    logger.info("Received request for /field_definitions")
    return jsonify(FIELD_DEFINITIONS)

@app.route('/storage_status', methods=['GET'])
def storage_status():
    """Get current storage configuration and status"""
    try:
        storage_info = storage_service.get_storage_info()
        config_validation = S3Config.validate_config()
        
        return jsonify({
            "storage_info": storage_info,
            "config_validation": config_validation,
            "templates_count": len(storage_service.list_templates()),
            "status": "healthy" if config_validation['valid'] else "warning"
        })
    except Exception as e:
        logger.error(f"Error getting storage status: {e}")
        return jsonify({"error": f"Error getting storage status: {str(e)}"}), 500

@app.route('/ai_remap_headers', methods=['POST'])
def ai_remap_headers():
    """Use Azure OpenAI to intelligently remap headers for a file"""
    logger.info("Received request for /ai_remap_headers")
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        file_identifier = data.get('file_identifier')
        headers = data.get('headers', [])
        
        if not file_identifier or not headers:
            return jsonify({"error": "Missing file_identifier or headers"}), 400
        
        logger.info(f"🤖 AI remapping {len(headers)} headers for file: {file_identifier}")
        
        # Use intelligent batch mapping
        mappings = header_mapper.generate_intelligent_batch_mapping(headers, FIELD_DEFINITIONS)
        
        # Analyze results
        high_confidence_count = sum(1 for m in mappings if m.get('confidence_score', 0) >= 80)
        total_mapped = len([m for m in mappings if m.get('mapped_field') != 'N/A'])
        
        response_data = {
            "success": True,
            "file_identifier": file_identifier,
            "field_mappings": mappings,
            "analysis": {
                "total_headers": len(headers),
                "high_confidence_mappings": high_confidence_count,
                "total_mapped": total_mapped,
                "unmapped": len(headers) - total_mapped
            },
            "message": f"🤖 AI analysis complete: {high_confidence_count} high-confidence mappings, {total_mapped} total mapped"
        }
        
        logger.info(f"✅ AI remapping complete for {file_identifier}: {high_confidence_count}/{len(headers)} high-confidence")
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error in AI header remapping: {e}", exc_info=True)
        return jsonify({"error": f"AI remapping failed: {str(e)}"}), 500

@app.route('/preview_file/<path:filename>', methods=['GET'])
def preview_file_route(filename):
    """Get a preview of the parsed/extracted file content."""
    logger.info(f"Received request to preview parsed content for file: {filename}")
    
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(file_path):
        logger.error(f"File not found for preview: {file_path}")
        return jsonify({"error": f"File not found: {filename}"}), 404
    
    try:
        # Check if we have cached extracted text data first
        if filename in EXTRACTED_TEXT_CACHE:
            logger.info(f"Using cached extracted text data for {filename}")
            cached_data = EXTRACTED_TEXT_CACHE[filename]
            
            # Get file info
            file_stats = os.stat(file_path)
            file_size = file_stats.st_size
            
            preview_data = {
                "filename": filename,
                "file_size": file_size,
                "file_type": cached_data.get("file_type", "UNKNOWN"),
                "extracted_text": cached_data.get("extracted_text", ""),
                "headers": cached_data.get("headers", []),
                "data_rows": cached_data.get("sample_rows", []),
                "total_rows": cached_data.get("total_rows", 0),
                "parsing_info": cached_data.get("parsing_info", "")
            }
            
            logger.info(f"Successfully returned cached preview data for {filename}")
            return jsonify(sanitize_data_for_json(preview_data))
        
        # Fallback to original logic if no cached data (for backward compatibility)
        logger.info(f"No cached data found for {filename}, falling back to re-processing")
        
        # Get file info
        file_stats = os.stat(file_path)
        file_size = file_stats.st_size
        
        # Determine file type
        _, file_extension = os.path.splitext(filename)
        file_extension = file_extension.lower()
        
        preview_data = {
            "filename": filename,
            "file_size": file_size,
            "file_type": file_extension.replace('.', '').upper(),
            "extracted_text": "",
            "headers": [],
            "data_rows": [],
            "total_rows": 0,
            "parsing_info": ""
        }
        
        # Use the same extraction logic as the upload process
        if file_extension in ['.csv']:
            try:
                # Try different skip_rows values to find the best data structure
                best_result = None
                best_skip_rows = 0
                max_data_rows = 0
                
                # Try skip_rows from 0 to 25 to find the best data structure
                for skip_rows in range(0, 26):
                    try:
                        headers_result = extract_headers(file_path, 'CSV', skip_rows=skip_rows)
                        if isinstance(headers_result, list) and len(headers_result) > 0:
                            # Extract sample data to see if we get actual data
                            all_headers_mapping = [{'original_header': header, 'mapped_field': header} for header in headers_result]
                            data_result = extract_data(file_path, 'CSV', all_headers_mapping, skip_rows=skip_rows)
                            if isinstance(data_result, list) and len(data_result) > max_data_rows:
                                max_data_rows = len(data_result)
                                best_result = {
                                    'headers': headers_result,
                                    'data_rows': data_result,
                                    'skip_rows': skip_rows
                                }
                                best_skip_rows = skip_rows
                    except:
                        continue
                
                if best_result:
                    preview_data["headers"] = best_result['headers']
                    preview_data["data_rows"] = best_result['data_rows']
                    preview_data["total_rows"] = len(best_result['data_rows'])
                    
                    # Generate extracted text using helper function
                    preview_data["extracted_text"] = generate_extracted_text(
                        filename=filename,
                        file_type="CSV",
                        headers=preview_data['headers'],
                        data_rows=preview_data['data_rows'],
                        total_rows=preview_data['total_rows']
                    )
                    preview_data["parsing_info"] = f"Successfully parsed CSV with {len(preview_data['headers'])} headers and {preview_data['total_rows']} rows (skipped {best_skip_rows} header rows)"
                else:
                    # Fallback: just try with skip_rows=0
                    headers_result = extract_headers(file_path, 'CSV', skip_rows=0)
                    if isinstance(headers_result, list):
                        preview_data["headers"] = headers_result
                        preview_data["parsing_info"] = f"Found {len(headers_result)} headers but no data rows could be extracted"
                    else:
                        preview_data["parsing_info"] = "Could not parse CSV file structure"
                    
                    # Final fallback: show raw CSV content as extracted text
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            lines = []
                            for i, line in enumerate(f):
                                if i >= 20:  # Show first 20 lines as preview
                                    lines.append("... (showing first 20 lines of CSV file)")
                                    break
                                lines.append(line.rstrip())
                            
                            preview_data["extracted_text"] = '\n'.join(lines)
                            preview_data["parsing_info"] += " - Showing raw CSV content as fallback"
                    except Exception as e_fallback:
                        logger.error(f"Error reading CSV file for fallback preview: {e_fallback}")
                        preview_data["extracted_text"] = f"Error reading CSV file: {str(e_fallback)}"
                        
            except Exception as e:
                logger.error(f"Error parsing CSV file {filename}: {e}")
                preview_data["extracted_text"] = f"Error parsing CSV: {str(e)}"
                preview_data["parsing_info"] = f"Failed to parse CSV: {str(e)}"
                
        elif file_extension in ['.xlsx', '.xls']:
            try:
                # Extract headers and data using the same method as upload
                headers_result = extract_headers(file_path, 'XLSX', skip_rows=0)
                if isinstance(headers_result, list):
                    preview_data["headers"] = headers_result
                    
                    # Extract sample data - create mappings for all headers to show all data
                    all_headers_mapping = [{'original_header': header, 'mapped_field': header} for header in headers_result]
                    data_result = extract_data(file_path, 'XLSX', all_headers_mapping, skip_rows=0)
                    if isinstance(data_result, list):
                        preview_data["data_rows"] = data_result  # All rows
                        preview_data["total_rows"] = len(data_result)
                        
                        # Generate extracted text using helper function
                        preview_data["extracted_text"] = generate_extracted_text(
                            filename=filename,
                            file_type="EXCEL",
                            headers=preview_data['headers'],
                            data_rows=preview_data['data_rows'],
                            total_rows=preview_data['total_rows']
                        )
                        preview_data["parsing_info"] = f"Successfully parsed Excel with {len(preview_data['headers'])} headers and {preview_data['total_rows']} rows"
                        
            except Exception as e:
                logger.error(f"Error parsing Excel file {filename}: {e}")
                preview_data["extracted_text"] = f"Error parsing Excel: {str(e)}"
                preview_data["parsing_info"] = f"Failed to parse Excel: {str(e)}"
                
        elif file_extension == '.pdf':
            try:
                # Check if we have cached PDF data first
                if filename in TEMP_PDF_DATA_FOR_EXTRACTION:
                    pdf_data = TEMP_PDF_DATA_FOR_EXTRACTION[filename]
                    preview_data["headers"] = pdf_data.get('headers', [])
                    preview_data["data_rows"] = pdf_data.get('data_rows', [])[:10]
                    preview_data["total_rows"] = len(pdf_data.get('data_rows', []))
                else:
                    # Extract fresh data using the same method as upload
                    pdf_result = extract_headers_from_pdf_tables(file_path)
                    if isinstance(pdf_result, dict) and "error" not in pdf_result:
                        preview_data["headers"] = pdf_result.get('headers', [])
                        preview_data["data_rows"] = pdf_result.get('data_rows', [])[:10]
                        preview_data["total_rows"] = len(pdf_result.get('data_rows', []))
                
                if preview_data["headers"]:
                    # Generate extracted text using helper function
                    preview_data["extracted_text"] = generate_extracted_text(
                        filename=filename,
                        file_type="PDF",
                        headers=preview_data['headers'],
                        data_rows=preview_data['data_rows'],
                        total_rows=preview_data['total_rows']
                    )
                    preview_data["parsing_info"] = f"Successfully parsed PDF with {len(preview_data['headers'])} headers and {preview_data['total_rows']} rows"
                else:
                    preview_data["extracted_text"] = "No structured data could be extracted from this PDF file."
                    preview_data["parsing_info"] = "PDF parsing completed but no tabular data found"
                        
            except Exception as e:
                logger.error(f"Error parsing PDF file {filename}: {e}")
                preview_data["extracted_text"] = f"Error parsing PDF: {str(e)}"
                preview_data["parsing_info"] = f"Failed to parse PDF: {str(e)}"
        
        else:
            preview_data["extracted_text"] = f"File type {file_extension} is not supported for content extraction."
            preview_data["parsing_info"] = f"Unsupported file type: {file_extension}"
        
        logger.info(f"Successfully generated parsed content preview for {filename}")
        return jsonify(sanitize_data_for_json(preview_data))
        
    except Exception as e:
        logger.error(f"Error generating parsed content preview for {filename}: {e}", exc_info=True)
        return jsonify({"error": f"Error generating preview: {str(e)}"}), 500

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
    """Health check endpoint for AWS App Runner - simplest possible successful response."""
    # Return an empty 200 OK response with no content
    return "", 200

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
@app.route('/debug_upload.html', methods=['GET'])
def debug_upload_page():
    """Serve debug upload page"""
    with open('debug_upload.html', 'r') as f:
        return f.read()

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

@app.route('/health/detailed')
def health_detailed():
    """Detailed health check with capabilities"""
    try:
        # Test basic functionality
        import pandas as pd
        import pdfplumber
        import magic
        
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "environment": "app_runner",
            "capabilities": {
                "pandas": pd.__version__,
                "pdfplumber": "available",
                "magic": "available",
                "azure_openai": azure_openai_configured if 'azure_openai_configured' in globals() else False
            },
            "storage": storage_service.get_storage_info() if 'storage_service' in globals() else {"backend": "unknown"}
        })
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.datetime.utcnow().isoformat()
        }), 500

if __name__ == '__main__':
    # For local development
    app.run(debug=True, host='0.0.0.0', port=8088)
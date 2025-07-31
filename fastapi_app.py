import sys
import os
import logging
from typing import List, Dict, Any, Optional, Union
import json
import datetime
import pandas as pd
import re
import magic
import io
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Depends, Request
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Set up root logger for startup diagnostics
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
root_logger.addHandler(handler)

# Log import-time debugging information
root_logger.info("App starting up - Python version: %s", sys.version)
root_logger.info("Working directory: %s", os.getcwd())

from file_parser import extract_headers, extract_data, extract_headers_from_pdf_tables
from azure_openai_client import test_azure_openai_connection, azure_openai_configured
from data_validator import validate_uniqueness, validate_invoice_via_api
from pdftocsv import extract_tables_from_file

# Check if we're running on AWS Lambda
IS_LAMBDA = os.environ.get('AWS_EXECUTION_ENV') is not None
STAGE_PREFIX = os.environ.get('STAGE_PREFIX', '')  # e.g., '/dev' or '/prod' for API Gateway stages

# Create the FastAPI app
app = FastAPI(
    title="Vendor Statements API",
    description="API for processing vendor statements",
    version="1.0.0",
    root_path=STAGE_PREFIX if IS_LAMBDA else "",  # Important for API Gateway integration
    openapi_prefix=STAGE_PREFIX if IS_LAMBDA else "",  # For OpenAPI docs to work correctly
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Set this to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
UPLOAD_FOLDER = 'uploads'
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB limit
TEMPLATES_DIR = "templates_storage"
LEARNED_PREFERENCES_DIR = "learned_preferences_storage"

# Load external API configs
INVOICE_VALIDATION_API_URL = os.getenv('INVOICE_VALIDATION_API_URL')
INVOICE_VALIDATION_API_KEY = os.getenv('INVOICE_VALIDATION_API_KEY')

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
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
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
if not INVOICE_VALIDATION_API_URL:
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

# Pydantic Models
class TemplateResponse(BaseModel):
    templates: List[Dict[str, Any]]

class TemplateDetailsResponse(BaseModel):
    template: Dict[str, Any]

class HealthResponse(BaseModel):
    status: str
    message: str
    azure_openai_status: Dict[str, Any]
    
class ChatbotSuggestMappingRequest(BaseModel):
    headers: List[str]

# API Routes
@app.get("/", tags=["Info"])
def root():
    """Get basic info about the API"""
    return {
        "message": "Vendor Statements API is running",
        "documentation": "/docs"
    }

@app.get("/health", tags=["Health"])
def health_check():
    """Health check for the application"""
    try:
        test_result = test_azure_openai_connection()
        return HealthResponse(
            status="ok", 
            message="Service is operational", 
            azure_openai_status=test_result
        )
    except Exception as e:
        return HealthResponse(
            status="warning", 
            message=f"Service running but with warnings: {str(e)}", 
            azure_openai_status={"success": False, "message": str(e)}
        )

@app.post("/upload", tags=["Files"])
async def upload_files(files: List[UploadFile] = File(...)):
    """
    Upload vendor statement files (PDF, CSV, XLS, XLSX)
    
    This endpoint processes uploaded files and extracts headers and data.
    
    - **files**: List of files to upload (multipart form)
    """
    results = []

    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Too many files uploaded (limit is 10).")

    if not files:
        raise HTTPException(status_code=400, detail="No files selected.")

    for file_storage in files:
        if file_storage and file_storage.filename:
            original_filename_for_vendor = file_storage.filename
            filename = file_storage.filename
            results_entry = {
                "filename": filename, "success": False, "message": "File processing started.",
                "file_type": "unknown", "headers": [], "field_mappings": [],
                "applied_template_name": None,
                "applied_template_filename": None,
                "skip_rows": 0
            }
            try:
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                
                # Save the uploaded file
                with open(file_path, "wb") as f:
                    f.write(await file_storage.read())
                
                # Reset file position for multiple reads
                await file_storage.seek(0)

                try:
                    raw_mime_type = magic.from_file(file_path, mime=True)
                    logger.info(f"[UPLOAD_DEBUG] Raw MIME type for {filename}: '{raw_mime_type}'")
                    
                    mime_type = raw_mime_type.lower() if raw_mime_type else None
                    logger.info(f"[UPLOAD_DEBUG] Normalized (lowercase) MIME type: '{mime_type}'")

                    detected_type_name = SUPPORTED_MIME_TYPES.get(mime_type)
                    logger.info(f"[UPLOAD_DEBUG] Initial detected_type_name from SUPPORTED_MIME_TYPES: '{detected_type_name}' (for mime_type '{mime_type}')")
                    
                    effective_filename_for_processing = filename
                    effective_file_path_for_processing = file_path

                    if detected_type_name == 'OCTET_STREAM':
                        logger.info(f"[UPLOAD_DEBUG] MIME type is application/octet-stream for {filename}. Attempting fallback using file extension.")
                        _, file_extension = os.path.splitext(filename)
                        file_extension_lower = file_extension.lower()
                        logger.info(f"[UPLOAD_DEBUG] File extension: '{file_extension}', Lowercase for fallback: '{file_extension_lower}'")
                        
                        fallback_type_name = EXTENSION_TO_TYPE_FALLBACK.get(file_extension_lower)
                        logger.info(f"[UPLOAD_DEBUG] Fallback type from EXTENSION_TO_TYPE_FALLBACK: '{fallback_type_name}' for ext '{file_extension_lower}'")

                        if fallback_type_name:
                            detected_type_name = fallback_type_name
                            logger.info(f"[UPLOAD_DEBUG] Updated detected_type_name to '{detected_type_name}' from file extension fallback")

                    # Handle PDF analysis and potential conversion to CSV
                    if detected_type_name == 'PDF':
                        logger.info(f"[UPLOAD_DEBUG] File '{filename}' detected as PDF. Processing PDF...")
                        
                        # Check if we should auto-convert PDF to CSV
                        tables = extract_tables_from_file(file_path)
                        if tables:
                            logger.info(f"[UPLOAD_DEBUG] Successfully extracted {len(tables)} table(s) from PDF '{filename}'")
                            
                            # Convert the first table to CSV
                            csv_filename = f"{os.path.splitext(filename)[0]}-converted.csv"
                            csv_path = os.path.join(UPLOAD_FOLDER, csv_filename)
                            
                            # Write the first table to CSV
                            tables[0].to_csv(csv_path, index=False)
                            logger.info(f"[UPLOAD_DEBUG] Converted first table from PDF '{filename}' to CSV '{csv_filename}'")
                            
                            # Update the filename and path for subsequent processing
                            effective_filename_for_processing = csv_filename
                            effective_file_path_for_processing = csv_path
                            detected_type_name = 'CSV'
                            
                            results_entry["message"] = f"PDF converted to CSV. {len(tables)} table(s) found."
                        else:
                            logger.warning(f"[UPLOAD_DEBUG] No tables found in PDF '{filename}'. Will process as regular PDF.")
                            # Store PDF data for later header extraction
                            try:
                                pdf_headers = extract_headers_from_pdf_tables(file_path)
                                if pdf_headers:
                                    TEMP_PDF_DATA_FOR_EXTRACTION[original_filename_for_vendor] = pdf_headers
                                    results_entry["headers"] = pdf_headers
                                    results_entry["success"] = True
                                    results_entry["file_type"] = "PDF"
                                    results_entry["message"] = "PDF processed successfully."
                                    results.append(results_entry)
                                    continue # Skip to next file
                                else:
                                    logger.warning(f"No headers found in PDF '{filename}' using direct extraction.")
                                    results_entry["message"] = "No tables found in PDF. Unable to extract headers."
                                    results_entry["success"] = False
                                    results.append(results_entry)
                                    continue # Skip to next file
                            except Exception as pdf_extraction_err:
                                logger.error(f"Error extracting headers from PDF '{filename}': {pdf_extraction_err}", exc_info=True)
                                results_entry["message"] = f"Error processing PDF: {str(pdf_extraction_err)}"
                                results_entry["success"] = False
                                results.append(results_entry)
                                continue # Skip to next file
                    
                    # For CSV/XLS/XLSX files, extract headers
                    if detected_type_name in ['CSV', 'XLS', 'XLSX']:
                        logger.info(f"[UPLOAD_DEBUG] File '{effective_filename_for_processing}' detected as {detected_type_name}. Extracting headers...")
                        
                        # We default to 0 skip rows for initial header extraction
                        headers = extract_headers(effective_file_path_for_processing, detected_type_name, skip_rows=0)
                        
                        if isinstance(headers, dict) and "error" in headers:
                            results_entry["message"] = f"Error extracting headers: {headers['error']}"
                            results_entry["success"] = False
                            results.append(results_entry)
                            continue # Skip to next file
                        
                        if not headers:
                            results_entry["message"] = "No headers found in file. Try using a template like 'Basic' (skip_rows=10) from the Manage Templates page."
                            results_entry["success"] = False
                            results.append(results_entry)
                            continue # Skip to next file
                        
                        # Update results with extracted headers
                        results_entry["headers"] = headers
                        results_entry["file_type"] = detected_type_name
                        results_entry["success"] = True
                        results_entry["message"] = f"Headers extracted from {detected_type_name} file."
                        
                        # Look for similar templates to auto-apply
                        # (Simplified for the FastAPI version - we'll let the frontend handle this)
                        
                        # Map headers to standard fields
                        mapped_fields = []
                        for header in headers:
                            mapping_result = header_mapper.map_header_to_field(header)
                            mapped_fields.append(mapping_result)
                        
                        results_entry["field_mappings"] = mapped_fields
                    else:
                        results_entry["message"] = f"Unsupported file type: {detected_type_name if detected_type_name else 'unknown'}"
                        results_entry["success"] = False
                    
                except Exception as e:
                    logger.error(f"Error processing {filename}: {e}", exc_info=True)
                    results_entry["message"] = f"Error processing file: {str(e)}"
                    results_entry["success"] = False
            
            except Exception as e:
                logger.error(f"Error saving {filename}: {e}", exc_info=True)
                results_entry["message"] = f"Error saving file: {str(e)}"
                results_entry["success"] = False
            
            results.append(results_entry)
    
    return JSONResponse(content=results)

@app.post("/chatbot_suggest_mapping", tags=["AI"])
async def chatbot_suggest_mapping(request: ChatbotSuggestMappingRequest):
    """
    Use AI to suggest field mappings for headers
    
    - **headers**: List of headers to map
    """
    headers = request.headers
    if not headers:
        raise HTTPException(status_code=400, detail="No headers provided")

    try:
        mapping_results = chatbot_service.suggest_field_mappings(headers)
        return {"success": True, "mappings": mapping_results}
    except Exception as e:
        logger.error(f"Error in chatbot mapping: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@app.post("/process_file_data", tags=["Files"])
async def process_file_data(
    filename: str = Form(...),
    skip_rows: int = Form(0),
    mappings: str = Form(...),  # JSON string of mappings
    file_type: str = Form(...)
):
    """
    Process file data using the provided mappings
    
    - **filename**: Name of the uploaded file
    - **skip_rows**: Number of rows to skip
    - **mappings**: JSON string of field mappings
    - **file_type**: Type of file (CSV, XLS, XLSX, PDF)
    """
    try:
        mappings_dict = json.loads(mappings)
        
        # Process file
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"File not found: {filename}")
        
        # Extract data using the file_parser module
        extracted_data = extract_data(file_path, file_type, skip_rows, mappings_dict)
        
        if isinstance(extracted_data, dict) and "error" in extracted_data:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": extracted_data["error"]}
            )
        
        # Basic data validation
        validation_results = validate_uniqueness(extracted_data)
        
        # External API validation if configured
        invoice_validation_results = []
        if INVOICE_VALIDATION_API_URL and extracted_data:
            try:
                for row in extracted_data:
                    result = validate_invoice_via_api(row, INVOICE_VALIDATION_API_URL, INVOICE_VALIDATION_API_KEY)
                    invoice_validation_results.append(result)
            except Exception as validation_err:
                logger.error(f"Error validating with external API: {validation_err}", exc_info=True)
        
        return {
            "success": True,
            "data": extracted_data,
            "validation": validation_results,
            "invoice_validation": invoice_validation_results,
            "row_count": len(extracted_data) if extracted_data else 0
        }
    
    except Exception as e:
        logger.error(f"Error processing file data: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@app.get("/list_templates", tags=["Templates"])
async def list_templates():
    """List available templates"""
    try:
        templates = []
        for filename in os.listdir(TEMPLATES_DIR):
            if filename.endswith('.json'):
                template_path = os.path.join(TEMPLATES_DIR, filename)
                try:
                    with open(template_path, 'r', encoding='utf-8') as f:
                        template_data = json.load(f)
                        
                    template_info = {
                        "filename": filename,
                        "name": template_data.get("name", "Unnamed Template"),
                        "vendor_name": template_data.get("vendor_name", "Unknown Vendor"),
                        "created_date": template_data.get("created_date", "Unknown"),
                        "num_mappings": len(template_data.get("mappings", {})) if isinstance(template_data.get("mappings"), dict) else 0
                    }
                    templates.append(template_info)
                except Exception as e:
                    logger.error(f"Error reading template file {filename}: {e}", exc_info=True)
                    continue
        
        return TemplateResponse(templates=templates)
    
    except Exception as e:
        logger.error(f"Error listing templates: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error listing templates: {str(e)}")

@app.get("/get_template_details/{template_filename}", tags=["Templates"])
async def get_template_details(template_filename: str):
    """Get details of a specific template"""
    try:
        template_path = os.path.join(TEMPLATES_DIR, template_filename)
        if not os.path.exists(template_path):
            raise HTTPException(status_code=404, detail=f"Template not found: {template_filename}")
        
        with open(template_path, 'r', encoding='utf-8') as f:
            template_data = json.load(f)
        
        return TemplateDetailsResponse(template=template_data)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting template details: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting template details: {str(e)}")

@app.post("/save_template", tags=["Templates"])
async def save_template(template_data: str = Form(...)):
    """Save a template for future use"""
    try:
        template = json.loads(template_data)
        
        if not template.get("name"):
            return JSONResponse(
                status_code=400, 
                content={"success": False, "message": "Template name is required"}
            )
        
        # Create a safe filename
        safe_name = re.sub(r'[^\w\-\.]', '_', template["name"]) + '.json'
        template_path = os.path.join(TEMPLATES_DIR, safe_name)
        
        # Add creation date if not present
        if "created_date" not in template:
            template["created_date"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        with open(template_path, 'w', encoding='utf-8') as f:
            json.dump(template, f, indent=2)
        
        return {
            "success": True, 
            "message": f"Template saved: {template['name']}", 
            "filename": safe_name
        }
    
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "Invalid template data format"}
        )
    except Exception as e:
        logger.error(f"Error saving template: {e}", exc_info=True)
        return JSONResponse(
            status_code=500, 
            content={"success": False, "message": f"Error saving template: {str(e)}"}
        )

@app.post("/apply_template", tags=["Templates"])
async def apply_template(
    template_filename: str = Form(...),
    file_identifier: str = Form(...),
    file_type: str = Form(...)
):
    """
    Apply a template to a specific uploaded file
    
    - **template_filename**: Name of the template file to apply
    - **file_identifier**: Name of the uploaded file
    - **file_type**: Type of file (CSV, XLS, XLSX, PDF)
    """
    logger.info(f"Applying template {template_filename} to file {file_identifier}")
    
    # Load template
    template_path = os.path.join(TEMPLATES_DIR, template_filename)
    if not os.path.exists(template_path):
        raise HTTPException(status_code=404, detail=f"Template file not found: {template_filename}")
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            template_data = json.load(f)
        
        # Validate template structure
        if "field_mappings" not in template_data:
            raise HTTPException(status_code=400, detail="Invalid template: missing field_mappings")
        
        skip_rows = template_data.get("skip_rows", 0)
        
        # Check if file exists
        file_path = os.path.join(UPLOAD_FOLDER, file_identifier)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"File not found: {file_identifier}")
        
        # Re-extract headers with the template's skip_rows
        logger.info(f"Re-extracting headers for {file_identifier} with skip_rows={skip_rows}")
        
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
                    raise HTTPException(status_code=400, detail="Error extracting headers from PDF")
        else:
            # For CSV/XLS/XLSX files
            headers_result = extract_headers(file_path, file_type, skip_rows=skip_rows)
            if isinstance(headers_result, dict) and "error" in headers_result:
                raise HTTPException(status_code=400, detail=f"Error extracting headers: {headers_result['error']}")
            headers = headers_result if isinstance(headers_result, list) else []
        
        if not headers:
            raise HTTPException(status_code=400, detail=f"No headers found with skip_rows={skip_rows}")
        
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
                auto_mapping = header_mapper.map_header_to_field(header)
                applied_mappings.append(auto_mapping)
        
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
        
        logger.info(f"Successfully applied template {template_filename} to {file_identifier}")
        return response_data
    
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error for {template_filename}: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid JSON in template file: {template_filename}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error applying template {template_filename}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error applying template: {str(e)}")

@app.delete("/delete_template/{template_filename}", tags=["Templates"])
async def delete_template(template_filename: str):
    """
    Delete a specific template file
    
    - **template_filename**: Name of the template file to delete
    """
    logger.info(f"Received request to delete template: {template_filename}")
    
    template_path = os.path.join(TEMPLATES_DIR, template_filename)
    
    if not os.path.exists(template_path):
        raise HTTPException(status_code=404, detail=f"Template file not found: {template_filename}")
    
    try:
        os.remove(template_path)
        logger.info(f"Successfully deleted template: {template_filename}")
        return {"message": f"Template '{template_filename}' deleted successfully."}
    
    except PermissionError as e:
        logger.error(f"Permission denied deleting {template_filename}: {e}")
        raise HTTPException(status_code=403, detail=f"Permission denied: Cannot delete template {template_filename}")
    except Exception as e:
        logger.error(f"Error deleting template {template_filename}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error deleting template: {str(e)}")

@app.get("/field_definitions", tags=["Templates"])
async def get_field_definitions():
    """Get field definitions for template creation"""
    return FIELD_DEFINITIONS

@app.post("/download_processed_data", tags=["Files"])
async def download_processed_data(data: str = Form(...), format: str = Form("csv")):
    """
    Download processed data in CSV or Excel format
    
    - **data**: JSON string of processed data
    - **format**: Output format (csv or xlsx)
    """
    try:
        processed_data = json.loads(data)
        if not processed_data:
            raise HTTPException(status_code=400, detail="No data to download")
        
        df = pd.DataFrame(processed_data)
        
        # Create an in-memory file-like object
        output = io.BytesIO()
        
        if format.lower() == "xlsx":
            # Write to Excel file
            df.to_excel(output, index=False, engine="openpyxl")
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"processed_data_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
        else:
            # Default to CSV
            df.to_csv(output, index=False)
            media_type = "text/csv"
            filename = f"processed_data_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.csv"
        
        # Reset pointer to the beginning of the stream
        output.seek(0)
        
        # Return the file as a streaming response
        return StreamingResponse(
            output,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid data format")
    except Exception as e:
        logger.error(f"Error creating download: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creating download: {str(e)}")

@app.post("/extract_headers", tags=["Files"])
async def extract_headers_api(
    filename: str = Form(...),
    file_type: str = Form(...),
    skip_rows: int = Form(0)
):
    """
    Extract headers from a file with the specified skip_rows value
    
    - **filename**: Name of the uploaded file
    - **file_type**: Type of file (CSV, XLS, XLSX, PDF)
    - **skip_rows**: Number of rows to skip before looking for headers
    """
    try:
        logger.info(f"Re-extracting headers for {filename} with skip_rows={skip_rows}")
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return {"success": False, "message": f"File not found: {filename}"}
        
        # Extract headers with the specified skip_rows
        headers_result = extract_headers(file_path, file_type, skip_rows=skip_rows)
        
        if isinstance(headers_result, dict) and "error" in headers_result:
            logger.error(f"Error extracting headers for {filename}: {headers_result['error']}")
            return {"success": False, "message": f"Error extracting headers: {headers_result['error']}"}
        
        if not headers_result:
            logger.warning(f"No headers found in {filename} with skip_rows={skip_rows}")
            return {"success": False, "message": f"No headers found with skip_rows={skip_rows}"}
        
        # Map headers to standard fields
        mapped_fields = []
        for header in headers_result:
            mapping_result = header_mapper.map_header_to_field(header)
            mapped_fields.append(mapping_result)
        
        return {
            "success": True,
            "filename": filename,
            "file_type": file_type,
            "headers": headers_result,
            "field_mappings": mapped_fields,
            "message": f"Headers extracted successfully with skip_rows={skip_rows}"
        }
    
    except Exception as e:
        logger.error(f"Error in extract_headers_api: {e}", exc_info=True)
        return {"success": False, "message": f"Server error: {str(e)}"}

@app.get("/debug", tags=["Debug"])
async def debug_info():
    """Debug endpoint for checking environment variables and configurations"""
    # Only return non-sensitive info
    debug_data = {
        "python_version": sys.version,
        "working_directory": os.getcwd(),
        "field_definitions_count": len(FIELD_DEFINITIONS),
        "templates_count": len(os.listdir(TEMPLATES_DIR)) if os.path.exists(TEMPLATES_DIR) else 0,
        "azure_openai_configured": azure_openai_configured,
        "invoice_validation_api_configured": bool(INVOICE_VALIDATION_API_URL),
    }
    return debug_data

# Main entry point for uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

import pandas as pd
import pdfplumber
import logging
from PIL import Image # For OCR
import pytesseract
from pdf2image import convert_from_path, pdfinfo_from_path # For OCR

logger = logging.getLogger('upload_history')

def get_headers_from_csv(file_path):
    """
    Reads a CSV file and returns its headers.
    """
    try:
        df = pd.read_csv(file_path, nrows=0) # Read only headers by getting 0 rows
        return df.columns.tolist()
    except pd.errors.EmptyDataError:
        return {"error": "The CSV file is empty."}
    except Exception as e:
        return {"error": f"Error parsing CSV: {str(e)}"}

def get_headers_from_excel(file_path):
    """
    Reads an Excel file (first sheet) and returns its headers.
    """
    try:
        # For Excel, pandas might need to read some data to find headers if they are not strictly on row 0.
        # Using nrows=0 might not always work as expected if the file has merged cells or specific formatting.
        # Reading the first row of data is generally safer for header detection.
        df = pd.read_excel(file_path, sheet_name=0, nrows=1) # Read first data row to get headers
        if df.empty and not pd.read_excel(file_path, sheet_name=0, header=None).empty:
             # If reading 1 row gives an empty df, but the sheet is not empty,
             # it might mean the first row is empty but headers are present.
             # Try to get headers without assuming data rows.
             df_header_only = pd.read_excel(file_path, sheet_name=0)
             return df_header_only.columns.tolist()
        return df.columns.tolist()
    except pd.errors.EmptyDataError: # Less common for Excel, but good to have
        return {"error": "The Excel sheet is empty or the first sheet has no data."}
    except Exception as e:
        # xlrd.biffh.XLRDError can happen for corrupted .xls files
        # zipfile.BadZipFile for corrupted .xlsx
        return {"error": f"Error parsing Excel: {str(e)}"}

def extract_headers(file_path, file_type):
    """
    Wrapper function to extract headers based on file type.
    """
    if file_type == "CSV":
        return get_headers_from_csv(file_path)
    elif file_type in ["XLSX", "XLS"]:
        return get_headers_from_excel(file_path)
    elif file_type == "PDF":
        pdf_extraction_result = extract_headers_from_pdf_tables(file_path)
        if isinstance(pdf_extraction_result, dict) and "error" in pdf_extraction_result:
            return pdf_extraction_result # Propagate error
        elif isinstance(pdf_extraction_result, dict) and "headers" in pdf_extraction_result:
            # If no suitable table was found, headers might be empty and a message will be in the result.
            # The main extract_headers function is expected to return a list of headers or an error dict.
            # So, if there's a message and empty headers, we might want to convey that.
            # For now, just return the headers list as per the contract.
            # The message from pdf_extraction_result can be logged or handled by caller if needed.
            if not pdf_extraction_result['headers'] and pdf_extraction_result.get('message'):
                 logger.info(f"PDF header extraction for {file_path}: {pdf_extraction_result['message']}")
                 # Return error structure if no headers found, to be consistent with other types failing
                 # Or, return empty list and let UI decide based on message.
                 # For consistency, if there's a specific message about *why* no headers, treat it as an info/error for app.py
                 return {"error": pdf_extraction_result['message']} # Use 'error' key to be caught by app.py's existing logic
            return pdf_extraction_result['headers']
        else: # Should not happen if extract_headers_from_pdf_tables works as expected
            logger.error(f"Unexpected result type from extract_headers_from_pdf_tables for {file_path}")
            return {"error": "Unexpected error during PDF header processing."}
    else:
        return {"error": f"Header extraction not supported for file type: {file_type}"}

if __name__ == '__main__':
    # Basic test cases (will only work if files exist at these paths)
    # Create dummy files for testing if needed
    # print(f"CSV Headers: {extract_headers('dummy.csv', 'CSV')}")
    # print(f"XLSX Headers: {extract_headers('dummy.xlsx', 'XLSX')}")
    # print(f"PDF Info: {extract_headers('dummy.pdf', 'PDF')}")
    pass

def extract_data(file_path, file_type, finalized_mappings, pdf_data_rows=None, pdf_original_headers=None):
    """
    Reads data from a file, filters, and renames columns based on finalized mappings.
    For PDFs, uses provided pdf_data_rows and pdf_original_headers.
    Returns a list of dictionaries, where each dictionary is a row, or an error dict.
    """
    try:
        df = None
        if file_type == "PDF":
            if pdf_data_rows is None or pdf_original_headers is None:
                logger.error("PDF data_rows or original_headers not provided to extract_data.")
                return {"error": "PDF data or headers not provided for data extraction."}
            if not pdf_original_headers and pdf_data_rows: # If headers are empty list, but data rows exist
                 logger.warning(f"PDF processed for {file_path} had data rows but no headers. Cannot create DataFrame meaningfully.")
                 return {"error": "PDF has data rows but no headers were identified from the selected table."}
            if not pdf_data_rows: # No data rows from the selected table
                 logger.info(f"No data rows found in the selected PDF table for {file_path}.")
                 return [] # Return empty list, as no data to process

            # Ensure headers are unique if pandas is to use them. If not, this might cause issues.
            # A more robust way would be to handle duplicate headers here if they are possible from pdfplumber extraction.
            df = pd.DataFrame(pdf_data_rows, columns=pdf_original_headers)
            if df.empty and pdf_original_headers: # DataFrame is empty but headers were provided (e.g. table had only header row)
                logger.info(f"PDF table for {file_path} contained only headers or no data rows after header.")
                return []


        elif file_type == "CSV":
            df = pd.read_csv(file_path)
        elif file_type in ["XLSX", "XLS"]:
            df = pd.read_excel(file_path, sheet_name=0)
        else:
            return {"error": f"Unsupported file type for data extraction: {file_type}"}

        if df is None: # Should be caught by specific type logic, but as a safeguard
             return {"error": "Could not load data into DataFrame."}

        if df.empty and not (file_type == "PDF" and pdf_original_headers): # For non-PDF, if df is empty, it's empty data. For PDF, handled above.
            logger.info(f"File {file_path} (type: {file_type}) is empty or contains no data.")
            return []

        columns_to_rename = {}
        columns_to_keep_original_names = []

        # df.columns provides the actual headers found in the file/selected PDF table
        actual_file_headers_set = set(df.columns.tolist())

        for fm_item in finalized_mappings:
            original_header = fm_item.get('original_header')
            mapped_field = fm_item.get('mapped_field')

            if mapped_field and mapped_field != 'N/A':
                if original_header in actual_file_headers_set:
                    columns_to_rename[original_header] = mapped_field
                    if original_header not in columns_to_keep_original_names: # Avoid duplicates
                        columns_to_keep_original_names.append(original_header)
                else:
                    logger.warning(f"Warning: Finalized mapping for original header '{original_header}' -> '{mapped_field}' but this header was not found in the source data for {file_path}.")

        if not columns_to_keep_original_names:
            logger.warning(f"No columns to keep for {file_path} after matching finalized mappings with actual headers. Returning empty data.")
            return [] # No columns matched or were mapped

        df_filtered = df[columns_to_keep_original_names]
        df_renamed = df_filtered.rename(columns=columns_to_rename)

        data = df_renamed.to_dict(orient='records')
        return data

    except FileNotFoundError:
        return {"error": f"File not found: {file_path}"}
    except pd.errors.EmptyDataError:
        return {"error": "The file is empty or contains no data to parse."}
    except Exception as e:
        # More specific pandas errors could be caught here if needed
        return {"error": f"Error processing file {file_path} for data extraction: {str(e)}"}

# --- PDF Text Extraction Functions ---

def _extract_text_from_pdf_page(page_object) -> str:
    """
    Extracts text from a single pdfplumber.page.Page object.
    Returns an empty string if no text or if extraction returns None.
    """
    if page_object:
        text = page_object.extract_text()
        return text if text else ""
    return ""

def extract_all_text_from_pdf(file_path: str) -> str:
    """
    Extracts all text content from a PDF file.
    Returns a single string with all text, pages separated by newlines.
    Returns an error string if an error occurs.
    """
    all_text_parts = []
    try:
        with pdfplumber.open(file_path) as pdf:
            if not pdf.pages:
                logger.warning(f"PDF file '{file_path}' contains no pages.")
                return "" # Or a specific message like "PDF has no pages."

            for i, page in enumerate(pdf.pages):
                try:
                    page_text = _extract_text_from_pdf_page(page)
                    all_text_parts.append(page_text)
                except Exception as e_page:
                    logger.error(f"Error extracting text from page {i+1} of PDF '{file_path}': {e_page}", exc_info=True)
                    all_text_parts.append(f"\n[Error extracting page {i+1}]\n") # Add placeholder for problematic page

            return "\n".join(all_text_parts).strip()

    except FileNotFoundError:
        logger.error(f"PDF file not found: {file_path}")
        return f"Error: File not found at {file_path}"
    except pdfplumber.exceptions.PDFSyntaxError as e_syntax: # Common for corrupted or non-standard PDFs
        logger.error(f"PDFSyntaxError for '{file_path}': {e_syntax}", exc_info=True)
        return f"Error: Could not parse PDF. File may be corrupted or not a standard PDF. (Details: {e_syntax})"
    except pdfplumber.exceptions.EncryptedPDFError as e_encrypted:
        logger.error(f"EncryptedPDFError for '{file_path}': {e_encrypted}", exc_info=True)
        return f"Error: PDF file '{file_path}' is encrypted and cannot be opened without a password."
    except Exception as e: # Catch-all for other pdfplumber or general errors
        logger.error(f"Unexpected error extracting text from PDF '{file_path}': {e}", exc_info=True)
        return f"Error: Could not extract text from PDF. (Details: {str(e)})"

# --- PDF Table Extraction Functions ---

def _find_and_extract_tables_on_page(page_object) -> list[list[list[str]]]:
    """
    Finds all tables on a single pdfplumber.page.Page object and extracts their data.
    Returns a list of tables, where each table is a list of rows, and each row is a list of cell strings.
    Returns an empty list if no tables are found or if errors occur during extraction of tables from a page.
    """
    extracted_page_tables = []
    if not page_object:
        return extracted_page_tables

    try:
        # Default table_settings are often good enough as a starting point.
        # Common alternatives: {"vertical_strategy": "lines", "horizontal_strategy": "lines"} for ruled tables
        # or {"vertical_strategy": "text", "horizontal_strategy": "text"} for tables based on text alignment.
        found_tables = page_object.find_tables(table_settings={})

        if not found_tables:
            # logger.info(f"No tables found on page {page_object.page_number}") # Can be too verbose
            return extracted_page_tables

        for table_obj in found_tables:
            try:
                extracted_table = table_obj.extract()
                if extracted_table: # Ensure extract() didn't return None or empty
                    # Clean cell data: replace None with empty string, ensure all are strings
                    cleaned_table = []
                    for row in extracted_table:
                        cleaned_row = [str(cell) if cell is not None else "" for cell in row]
                        cleaned_table.append(cleaned_row)
                    extracted_page_tables.append(cleaned_table)
            except Exception as e_extract_table:
                logger.error(f"Error extracting data from a specific table on page {page_object.page_number}: {e_extract_table}", exc_info=True)
                # Optionally add a placeholder or skip this table
    except Exception as e_find_tables:
        # This might catch errors from find_tables() itself if page structure is very unusual
        logger.error(f"Error finding tables on page {page_object.page_number}: {e_find_tables}", exc_info=True)

    return extracted_page_tables


def extract_all_tables_from_pdf(file_path: str) -> list: # Returns list of tables, or dict with error
    """
    Extracts all tables from all pages of a PDF file.
    Each table is represented as a list of lists of strings.
    Returns a list of all tables found, or an error dictionary.
    """
    all_tables_from_pdf = []
    try:
        with pdfplumber.open(file_path) as pdf:
            if not pdf.pages:
                logger.warning(f"PDF file '{file_path}' contains no pages. No tables to extract.")
                return [] # Return empty list if no pages

            for i, page in enumerate(pdf.pages):
                try:
                    tables_on_page = _find_and_extract_tables_on_page(page)
                    if tables_on_page:
                        all_tables_from_pdf.extend(tables_on_page)
                except Exception as e_page_process:
                    logger.error(f"Error processing tables on page {i+1} of PDF '{file_path}': {e_page_process}", exc_info=True)
                    # Decide if an error on one page should stop all, or just skip that page's tables.
                    # For now, we log and continue.

            logger.info(f"Found {len(all_tables_from_pdf)} table(s) in total in PDF '{file_path}'.")
            return all_tables_from_pdf

    except FileNotFoundError:
        logger.error(f"PDF file not found for table extraction: {file_path}")
        return {"error": f"File not found: {file_path}"}
    except pdfplumber.exceptions.PDFSyntaxError as e_syntax:
        logger.error(f"PDFSyntaxError during table extraction for '{file_path}': {e_syntax}", exc_info=True)
        return {"error": f"Could not parse PDF for table extraction. File may be corrupted. (Details: {e_syntax})"}
    except pdfplumber.exceptions.EncryptedPDFError as e_encrypted:
        logger.error(f"EncryptedPDFError during table extraction for '{file_path}': {e_encrypted}", exc_info=True)
        return {"error": f"PDF file '{file_path}' is encrypted and cannot be opened for table extraction."}
    except Exception as e:
        logger.error(f"Unexpected error extracting tables from PDF '{file_path}': {e}", exc_info=True)
        return {"error": f"Could not extract tables from PDF. (Details: {str(e)})"}

def extract_headers_from_pdf_tables(file_path: str) -> dict:
    """
    Extracts headers from the most likely primary table in a PDF.
    Also returns the selected table's data and index for further processing.
    Note: OCR (Tesseract) and PDF to image conversion (Poppler) are optional diagnostics
    and require external system dependencies to be installed.
    """
    all_tables_from_pdf = extract_all_tables_from_pdf(file_path)
    ocr_diagnostic_message = ""

    if isinstance(all_tables_from_pdf, dict) and "error" in all_tables_from_pdf:
        logger.error(f"Error received from extract_all_tables_from_pdf for {file_path}: {all_tables_from_pdf['error']}")
        # Even if table extraction failed, try OCR if it's a file access issue for pdfplumber but not for pdf2image
        # This is unlikely but provides a fallback path for OCR diagnostic.
        # However, if it's a fundamental PDF issue, OCR might also fail.
        # For now, let's only attempt OCR if pdfplumber found NO tables, not if it errored out.
        return all_tables_from_pdf

    if not all_tables_from_pdf:
        logger.info(f"No tables found in PDF {file_path} by pdfplumber. Checking text content...")
        # Check total text content from pdfplumber to decide on OCR diagnostic
        pdf_text_content = extract_all_text_from_pdf(file_path)
        if isinstance(pdf_text_content, str) and len(pdf_text_content) < 100 : # Low text threshold
            logger.warning(f"Minimal text ({len(pdf_text_content)} chars) extracted by pdfplumber from {file_path}. Attempting OCR diagnostic on first page.")
            try:
                # Check if PDF has pages before attempting conversion
                info = pdfinfo_from_path(file_path, userpw=None, poppler_path=None)
                if info.get('Pages', 0) > 0:
                    images = convert_from_path(file_path, first_page=1, last_page=1, poppler_path=None) # Specify poppler_path if not in PATH
                    if images:
                        first_page_image = images[0]
                        ocr_text = pytesseract.image_to_string(first_page_image)
                        logger.info(f"OCR Diagnostic Text (first 500 chars) from first page of {file_path}:\n{ocr_text[:500]}...")
                        if ocr_text.strip():
                            ocr_diagnostic_message = " OCR diagnostic on first page yielded some text. This might indicate a scanned PDF."
                        else:
                            ocr_diagnostic_message = " OCR diagnostic on first page yielded no text."
                    else:
                        msg = f"Could not convert first page of {file_path} to image for OCR diagnostic (pdf2image returned no images)."
                        logger.warning(msg)
                        ocr_diagnostic_message = f" {msg}"
                else:
                    msg = f"PDF {file_path} has 0 pages according to pdfinfo. Skipping OCR diagnostic."
                    logger.warning(msg)
                    ocr_diagnostic_message = f" {msg}"

            except Exception as e_ocr: # Catch exceptions from pdf2image or pytesseract
                logger.error(f"Error during OCR diagnostic attempt for {file_path}: {e_ocr}", exc_info=True)
                ocr_diagnostic_message = f" OCR diagnostic failed: {str(e_ocr)}."

        base_message = 'No tables found in PDF via direct extraction.' + ocr_diagnostic_message
        return {'headers': [], 'selected_table_index': -1, 'selected_table_data': [], 'data_rows': [], 'message': base_message}

    selected_table_index = -1
    primary_table_data = None

    # Primary Table Selection Logic: First table with at least 2 rows and 2 columns
    for i, table_data in enumerate(all_tables_from_pdf):
        if len(table_data) >= 2 and len(table_data[0]) >= 1: # Check for at least 2 rows and 1 column (for header + data)
                                                            # A stricter 2 column check might be len(table_data[0]) >= 2
            # Let's refine: check if first row (potential header) has at least one non-empty cell
            # And if there's at least one data row.
            potential_header_row = table_data[0]
            if any(str(cell).strip() for cell in potential_header_row): # Header has content
                primary_table_data = table_data
                selected_table_index = i
                logger.info(f"Selected table {selected_table_index} as primary from PDF '{file_path}' (out of {len(all_tables_from_pdf)} tables).")
                break

    if primary_table_data is None:
        logger.info(f"No suitable primary table found in PDF '{file_path}' (min 2 rows, 1+ col, content in header).")
        return {'headers': [], 'selected_table_index': -1, 'selected_table_data': [], 'data_rows': [], 'message': 'No suitable primary table found.'}

    # Header Identification from Primary Table
    header_row_list = primary_table_data[0]
    headers = [str(cell).strip() if cell is not None else "" for cell in header_row_list]

    data_rows = primary_table_data[1:] # Rows after the header row

    logger.info(f"Extracted {len(headers)} headers from selected table in PDF '{file_path}'. Headers: {headers}")

    return {
        'headers': headers,
        'selected_table_data': primary_table_data,
        'selected_table_index': selected_table_index,
        'data_rows': data_rows, # Adding data_rows for potential use in extract_data
        'message': 'Headers extracted successfully from PDF table.'
    }

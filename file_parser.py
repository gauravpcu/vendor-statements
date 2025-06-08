import pandas as pd
import pdfplumber
import logging
from PIL import Image
import pytesseract
from pytesseract import Output as PytesseractOutput
from pdf2image import convert_from_path, pdfinfo_from_path

logger = logging.getLogger('upload_history')

def get_headers_from_csv(file_path, skip_rows=0):
    """
    Reads a CSV file and returns its headers, skipping specified number of rows.
    """
    try:
        # nrows=0 should read no data rows, but infer columns from the first non-skipped line
        df_header = pd.read_csv(file_path, skiprows=skip_rows, nrows=0)
        headers = df_header.columns.tolist()
        if not headers: # If skiprows resulted in reading an empty part of the file or beyond content
             logger.warning(f"No headers found in CSV '{file_path}' after skipping {skip_rows} rows.")
             return [] # Return empty list, not an error, to signify no headers found at that position
        return headers
    except pd.errors.EmptyDataError: # This might happen if skip_rows is beyond the file content
        logger.warning(f"EmptyDataError for CSV '{file_path}' after skipping {skip_rows} rows. Likely skipped too many rows.")
        return [] # No headers found
    except Exception as e:
        logger.error(f"Error parsing CSV '{file_path}' with skip_rows={skip_rows}: {e}", exc_info=True)
        return {"error": f"Error parsing CSV: {str(e)}"}

def get_headers_from_excel(file_path, skip_rows=0):
    """
    Reads an Excel file (first sheet) and returns its headers, skipping specified number of rows.
    """
    try:
        # nrows=0 should get columns from the first non-skipped row
        df_header = pd.read_excel(file_path, sheet_name=0, skiprows=skip_rows, nrows=0)
        headers = df_header.columns.tolist()
        if not headers: # If skiprows resulted in reading an empty part of the file
            logger.warning(f"No headers found in Excel '{file_path}' after skipping {skip_rows} rows.")
            return []
        return headers
    except pd.errors.EmptyDataError: # xlrd can raise this, or if sheet is truly empty after skip
        logger.warning(f"EmptyDataError for Excel '{file_path}' after skipping {skip_rows} rows.")
        return []
    except Exception as e:
        # Handle specific exceptions like XLRDError for .xls if necessary, or BadZipFile for .xlsx
        logger.error(f"Error parsing Excel '{file_path}' with skip_rows={skip_rows}: {e}", exc_info=True)
        return {"error": f"Error parsing Excel: {str(e)}"}

def extract_headers(file_path, file_type, skip_rows=0):
    """
    Wrapper function to extract headers based on file type, with optional row skipping for CSV/Excel.
    """
    if file_type == "CSV":
        return get_headers_from_csv(file_path, skip_rows=skip_rows)
    elif file_type in ["XLSX", "XLS"]:
        return get_headers_from_excel(file_path, skip_rows=skip_rows)
    elif file_type == "PDF":
        # skip_rows is not applicable to PDF table extraction logic currently
        if skip_rows > 0:
            logger.info(f"skip_rows parameter is not used for PDF header extraction. Processing PDF '{file_path}' from the beginning.")
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

def extract_data(file_path, file_type, finalized_mappings, skip_rows=0, raw_pdf_table_content=None):
    """
    Reads data from a file, filters, and renames columns based on finalized mappings.
    For PDFs, uses provided raw_pdf_table_content { 'headers': [], 'data_rows': [[]] }.
    For CSV/Excel, uses skip_rows to ignore initial rows before header.
    Returns a list of dictionaries, where each dictionary is a row, or an error dict.
    """
    try:
        df = None
        if file_type == "PDF":
            if raw_pdf_table_content is None or \
               not isinstance(raw_pdf_table_content, dict) or \
               'headers' not in raw_pdf_table_content or \
               'data_rows' not in raw_pdf_table_content:
                logger.error("PDF raw_pdf_table_content not provided or invalid for extract_data.")
                return {"error": "PDF content (headers/data rows) not provided or invalid for data extraction."}

            pdf_original_headers = raw_pdf_table_content['headers']
            pdf_data_rows = raw_pdf_table_content['data_rows']

            if not pdf_original_headers and pdf_data_rows:
                 logger.warning(f"PDF processed for {file_path} had data rows but no headers (from raw_pdf_table_content). Cannot create DataFrame meaningfully.")
                 return {"error": "PDF has data rows but no headers were identified from the selected table (via raw_pdf_table_content)."}

            # If there are headers but no data rows, an empty list of dicts is valid if mappings match headers.
            # If there are no data_rows, df will be empty.
            # If there are no headers, df will have default 0,1,2... headers.

            df = pd.DataFrame(pdf_data_rows, columns=pdf_original_headers if pdf_original_headers else None)

            if df.empty and not pdf_data_rows: # If data_rows was empty to begin with
                logger.info(f"No data rows provided in raw_pdf_table_content for PDF {file_path}. Returning empty list.")
                return []
            # If df is empty but there were data_rows, it might be due to pd.DataFrame behavior with certain inputs.
            # However, with list of lists (data_rows) and list (headers), it should generally work or raise error.

        elif file_type == "CSV":
            # For CSV, the header for data extraction is determined by skip_rows.
            # Pandas will use the first row after skipping as the header.
            df = pd.read_csv(file_path, skiprows=skip_rows)
        elif file_type in ["XLSX", "XLS"]:
            # Similarly for Excel.
            df = pd.read_excel(file_path, sheet_name=0, skiprows=skip_rows)
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

                        # Perform OCR to get structured data
                        ocr_data = pytesseract.image_to_data(first_page_image, output_type=PytesseractOutput.DICT, lang='eng')

                        lines = {} # key: (block_num, par_num, line_num), value: list of word dicts
                        conf_threshold = 40 # Confidence threshold for words

                        for i in range(len(ocr_data['text'])):
                            word_text = ocr_data['text'][i].strip()
                            word_conf = int(ocr_data['conf'][i])

                            if word_conf > conf_threshold and word_text:
                                line_key = (
                                    ocr_data['block_num'][i],
                                    ocr_data['par_num'][i],
                                    ocr_data['line_num'][i]
                                )
                                if line_key not in lines:
                                    lines[line_key] = []
                                lines[line_key].append({
                                    'text': word_text,
                                    'left': int(ocr_data['left'][i]), # Ensure int for sorting
                                    'top': int(ocr_data['top'][i]),
                                    'width': int(ocr_data['width'][i]),
                                    'height': int(ocr_data['height'][i])
                                })

                        reconstructed_rows = []
                        for line_key in sorted(lines.keys()): # Sort by block, paragraph, line number
                            sorted_words_in_line = sorted(lines[line_key], key=lambda w: w['left'])
                            reconstructed_rows.append([word['text'] for word in sorted_words_in_line])

                        reconstructed_lines_with_coords = [] # List of lines, where each line is list of word dicts
                        for line_key in sorted(lines.keys()):
                            reconstructed_lines_with_coords.append(sorted(lines[line_key], key=lambda w: w['left']))

                        ocr_grid_data = []
                        max_cols = 0

                        if reconstructed_lines_with_coords:
                            # Estimate average character width for GAP_THRESHOLD (very rough)
                            avg_char_width = 5 # Default if no words found
                            total_width = 0
                            total_chars = 0
                            for line in reconstructed_lines_with_coords:
                                for word in line:
                                    total_width += word['width']
                                    total_chars += len(word['text'])
                            if total_chars > 0:
                                avg_char_width = total_width / total_chars

                            GAP_THRESHOLD = avg_char_width * 1.8 # Heuristic, e.g., 1.8 average character widths

                            for line_coords in reconstructed_lines_with_coords:
                                if not line_coords: continue
                                current_row_cells = []
                                current_cell_text = line_coords[0]['text']
                                for i in range(1, len(line_coords)):
                                    prev_word_end = line_coords[i-1]['left'] + line_coords[i-1]['width']
                                    current_word_start = line_coords[i]['left']
                                    gap = current_word_start - prev_word_end

                                    if gap > GAP_THRESHOLD:
                                        current_row_cells.append(current_cell_text.strip())
                                        current_cell_text = line_coords[i]['text']
                                    else:
                                        current_cell_text += " " + line_coords[i]['text']
                                current_row_cells.append(current_cell_text.strip())
                                ocr_grid_data.append(current_row_cells)

                            if ocr_grid_data:
                                for row in ocr_grid_data: # Calculate max_cols based on actual grid
                                    max_cols = max(max_cols, len(row))
                                for row in ocr_grid_data: # Normalize grid
                                    while len(row) < max_cols:
                                        row.append("")

                            logger.info(f"OCR Grid Reconstruction POC (first 5 rows, {max_cols} max cols) from {file_path}: {ocr_grid_data[:5]}")
                            ocr_diagnostic_message = f" OCR Grid POC: Reconstructed grid with {len(ocr_grid_data)} rows and {max_cols} max columns."
                            # Store ocr_grid_data in the result for this function
                            # This is a deviation from just returning headers, but necessary for PDF OCR path
                            # The main extract_headers will need to handle this dict structure for PDF if OCR was attempted.
                            # However, the plan is that extract_headers just returns the headers list.
                            # So, we'll add 'ocr_grid_data' to the dict that extract_headers_from_pdf_tables returns.

                            # Now, if ocr_grid_data was successfully created and is not empty:
                            if ocr_grid_data and len(ocr_grid_data) >= 1: # Need at least one row for headers
                                potential_ocr_headers_list = ocr_grid_data[0]
                                cleaned_ocr_headers = [str(cell).strip() for cell in potential_ocr_headers_list]

                                # Update the return dictionary with OCR-derived headers and data
                                # This effectively makes the OCR result the primary if pdfplumber found nothing.
                                base_message = 'No tables found by pdfplumber.' + ocr_diagnostic_message + " Headers identified from OCR data."
                                logger.info(f"Using OCR-derived headers for {file_path}: {cleaned_ocr_headers}")
                                return {
                                    'headers': cleaned_ocr_headers,
                                    'selected_table_index': 'ocr_derived', # Special index for OCR source
                                    'selected_table_data': ocr_grid_data, # The full grid from OCR
                                    'data_rows': ocr_grid_data[1:] if len(ocr_grid_data) > 1 else [], # Data rows are the rest
                                    'message': base_message,
                                    'ocr_grid_data': ocr_grid_data # Keep this for any further diagnostics if needed
                                }
                            else: # ocr_grid_data is empty or no rows
                                ocr_diagnostic_message += " OCR data did not yield a usable table structure."
                                logger.info(f"OCR data for {file_path} did not yield a usable table structure.")
                        else: # No reconstructed_lines_with_coords
                            logger.info(f"OCR POC for {file_path}: No text lines reconstructed to form a grid.")
                            ocr_diagnostic_message = " OCR POC: No text lines reconstructed to form a grid."
                    else: # No images from pdf2image
                        msg = f"Could not convert first page of {file_path} to image for OCR diagnostic."
                        logger.warning(msg)
                        ocr_diagnostic_message = f" {msg}"
                else:
                    msg = f"PDF {file_path} has 0 pages according to pdfinfo. Skipping OCR diagnostic."
                    logger.warning(msg)
                    ocr_diagnostic_message = f" {msg}"

            except Exception as e_ocr: # Catch exceptions from pdf2image or pytesseract
                logger.error(f"Error during OCR diagnostic attempt for {file_path}: {e_ocr}", exc_info=True)
                ocr_diagnostic_message = f" OCR diagnostic failed: {str(e_ocr)}."

        # This path is reached if OCR was attempted but didn't result in usable headers, or if OCR wasn't attempted due to sufficient pdfplumber text.
        base_message = 'No tables found in PDF via direct extraction.' + ocr_diagnostic_message
        return {'headers': [], 'selected_table_index': -1, 'selected_table_data': [], 'data_rows': [], 'message': base_message}

    # This part is for when pdfplumber *did* find tables.
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

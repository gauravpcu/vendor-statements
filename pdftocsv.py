import logging
import time
from pathlib import Path
import pandas as pd
import io
import sys
import os
import pdfplumber

_log = logging.getLogger(__name__)

def is_running_on_lambda():
    """Check if the code is running on AWS Lambda"""
    return os.environ.get('AWS_EXECUTION_ENV') is not None

def extract_tables_from_file_lambda(input_doc_path_str: str, output_csv_path_str: str | None = None):
    """
    Extract tables from a PDF file using pdfplumber (Lambda-compatible version without docling)
    """
    logging.basicConfig(level=logging.INFO)

    input_doc_path = Path(input_doc_path_str)

    if not input_doc_path.is_file():
        _log.error(f"Input file not found: {input_doc_path}")
        return []

    # Determine output path
    if output_csv_path_str:
        _log.info(f"Output path provided: {output_csv_path_str}")
        output_csv_path = Path(output_csv_path_str)
        output_dir = output_csv_path.parent
        doc_filename_for_output = output_csv_path.stem
    else:
        _log.info(f"No output path provided. Using default output path in 'scratch' directory for {input_doc_path.name}.")
        # If no output path is provided, use the 'scratch' directory
        output_dir = Path("scratch")
        doc_filename_for_output = input_doc_path.stem
        output_csv_path = output_dir / f"{doc_filename_for_output}-all_tables.csv"

    output_dir.mkdir(parents=True, exist_ok=True)

    start_time = time.time()
    all_tables = []

    try:
        # Use pdfplumber to extract tables
        with pdfplumber.open(input_doc_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                tables = page.extract_tables()
                if tables:
                    for table_idx, table in enumerate(tables):
                        # Convert table to DataFrame
                        df = pd.DataFrame(table[1:], columns=table[0] if table else [])
                        all_tables.append(df)
                        _log.info(f"Extracted table {table_idx + 1} from page {page_num + 1}")
    except Exception as e:
        _log.error(f"Error extracting tables using pdfplumber: {e}")
        return []

    # Function to sanitize DataFrame cells
    def sanitize_df_for_csv(df):
        # Trim whitespace from string cells
        df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

        # Prevent CSV injection
        def prevent_csv_injection(val):
            if isinstance(val, str) and val.startswith(('.', '=', '+', '-', '@')):
                return "'" + val  # Prepend a single quote
            return val

        df = df.applymap(prevent_csv_injection)
        return df

    all_csv_parts = []

    # Export tables
    for table_ix, table in enumerate(all_tables):
        table_df = sanitize_df_for_csv(table)
        
        # Convert table to CSV string via buffer
        csv_buffer = io.StringIO()
        current_table_df_for_csv = table_df.reset_index(drop=True)
        # Include header only for the first table
        current_table_df_for_csv.to_csv(csv_buffer, index=False, header=(table_ix == 0))
        all_csv_parts.append(csv_buffer.getvalue())
        csv_buffer.close()
        _log.info(f"Added table {table_ix + 1} to CSV parts.")

    # Save combined CSV file
    if all_csv_parts:
        combined_csv_content = "".join(all_csv_parts)
        # Use the determined output_csv_path
        _log.info(f"Saving all CSV tables to {output_csv_path}")
        with open(output_csv_path, 'w', encoding='utf-8') as f:
            f.write(combined_csv_content)
    else:
        _log.info("No tables found to create a combined CSV file.")

    end_time = time.time() - start_time
    _log.info(f"Document converted and tables exported in {end_time:.2f} seconds.")
    
    return all_tables if all_tables else []

def extract_tables_from_file_docling(input_doc_path_str: str, output_csv_path_str: str | None = None):
    """
    Extract tables from a PDF file using docling (more accurate but not Lambda-compatible)
    """
    from docling.document_converter import DocumentConverter
    
    logging.basicConfig(level=logging.INFO)

    input_doc_path = Path(input_doc_path_str)

    if not input_doc_path.is_file():
        _log.error(f"Input file not found: {input_doc_path}")
        return []

    # Determine output path
    if output_csv_path_str:
        print(f"Output path provided: {output_csv_path_str}")
        output_csv_path = Path(output_csv_path_str)
        output_dir = output_csv_path.parent
        doc_filename_for_output = output_csv_path.stem # Use this if specific name is given
    else:
        print(f"No output path provided. Using default output path in 'scratch' directory for {input_doc_path.name}.")
        # If no output path is provided, use the 'scratch' directory
        # Default behavior: use 'scratch' directory and input filename
        output_dir = Path("scratch")
        doc_filename_for_output = input_doc_path.stem
        output_csv_path = output_dir / f"{doc_filename_for_output}-all_tables.csv"

    output_dir.mkdir(parents=True, exist_ok=True)

    doc_converter = DocumentConverter()

    start_time = time.time()
    conv_res = doc_converter.convert(input_doc_path)
    all_tables = []

    # Function to sanitize DataFrame cells
    def sanitize_df_for_csv(df):
        # Trim whitespace from string cells
        df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

        # Prevent CSV injection
        def prevent_csv_injection(val):
            if isinstance(val, str) and val.startswith(('.', '=', '+', '-', '@')):  # Added '.' to the list
                return "'" + val  # Prepend a single quote
            return val

        df = df.applymap(prevent_csv_injection)
        return df

    all_csv_parts = []

    # Export tables
    for table_ix, table in enumerate(conv_res.document.tables):
        table_df: pd.DataFrame = table.export_to_dataframe()
        all_tables.append(table_df)
        
        # Convert table to CSV string via buffer
        csv_buffer = io.StringIO()
        current_table_df_for_csv = table_df.reset_index(drop=True)
        # Include header only for the first table
        current_table_df_for_csv.to_csv(csv_buffer, index=False, header=(table_ix == 0))
        all_csv_parts.append(csv_buffer.getvalue())
        csv_buffer.close()
        _log.info(f"Added table {table_ix + 1} to CSV parts.")

    # Save combined CSV file
    if all_csv_parts:
        combined_csv_content = "".join(all_csv_parts)
        # Use the determined output_csv_path
        _log.info(f"Saving all CSV tables to {output_csv_path}")
        with open(output_csv_path, 'w', encoding='utf-8') as f:
            f.write(combined_csv_content)
    else:
        _log.info("No tables found to create a combined CSV file.")

    end_time = time.time() - start_time
    _log.info(f"Document converted and tables exported in {end_time:.2f} seconds.")
    
    return all_tables

def extract_tables_from_file(input_doc_path_str: str, output_csv_path_str: str | None = None):
    """
    Extract tables from a file. Uses the appropriate method based on environment.
    
    In AWS Lambda: Use pdfplumber (lighter, no torch dependency)
    In local dev: Use docling if available (better accuracy) or pdfplumber as fallback
    """
    if is_running_on_lambda():
        _log.info("Running in Lambda environment, using pdfplumber for PDF table extraction")
        return extract_tables_from_file_lambda(input_doc_path_str, output_csv_path_str)
    else:
        try:
            # Try using docling first (better table extraction)
            _log.info("Using docling for PDF table extraction")
            return extract_tables_from_file_docling(input_doc_path_str, output_csv_path_str)
        except ImportError as e:
            # Fallback to pdfplumber if docling is not available
            _log.info(f"Docling not available ({e}), falling back to pdfplumber for table extraction")
            return extract_tables_from_file_lambda(input_doc_path_str, output_csv_path_str)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        file_path_arg = sys.argv[1]
        output_path_arg = None
        if len(sys.argv) > 2:
            output_path_arg = sys.argv[2]
        extract_tables_from_file(file_path_arg, output_path_arg)
    else:
        _log.warning("No input file provided. Running with default input and output.")
        default_input = "/Users/gaurav/Desktop/Code/docling/NHCA.xlsx"
        default_output = f"scratch/{Path(default_input).stem}-all_tables.csv"
        extract_tables_from_file(default_input, default_output)
import logging
import time
from pathlib import Path
import pandas as pd
import io
import sys
import os
import pdfplumber
import re

_log = logging.getLogger(__name__)

def is_valid_table(table_data):
    """
    Check if extracted table data represents a valid data table
    """
    if not table_data or len(table_data) < 2:
        return False
    
    # Check if we have at least 2 columns
    if not table_data[0] or len(table_data[0]) < 2:
        return False
    
    # Check if most rows have similar number of columns
    row_lengths = [len(row) for row in table_data if row]
    if not row_lengths:
        return False
    
    max_cols = max(row_lengths)
    min_cols = min(row_lengths)
    
    # If column count varies too much, it's probably not a proper table
    if max_cols - min_cols > max_cols * 0.5:
        return False
    
    # Check if we have at least 3 rows (header + 2 data rows minimum)
    if len(table_data) < 3:
        return False
    
    return True

def clean_table_data(table_data):
    """
    Clean and normalize table data
    """
    if not table_data:
        return []
    
    cleaned_table = []
    max_cols = max(len(row) for row in table_data if row)
    
    for row in table_data:
        if not row:
            continue
        
        # Pad row to max columns
        cleaned_row = row + [''] * (max_cols - len(row))
        
        # Clean cell content
        cleaned_row = [
            str(cell).strip() if cell is not None else ''
            for cell in cleaned_row
        ]
        
        # Skip rows that are mostly empty
        non_empty_cells = [cell for cell in cleaned_row if cell]
        if len(non_empty_cells) >= max_cols * 0.3:  # At least 30% of cells have content
            cleaned_table.append(cleaned_row)
    
    return cleaned_table

def has_table_like_headers(first_row):
    """
    Check if the first row looks like table headers
    """
    if not first_row:
        return False
    
    # Common header patterns
    header_patterns = [
        r'date|invoice|amount|description|quantity|price|total|item|product',
        r'line|ref|customer|vendor|account|number|code',
        r'po|order|bill|payment|balance|due'
    ]
    
    header_text = ' '.join(str(cell).lower() for cell in first_row if cell)
    
    for pattern in header_patterns:
        if re.search(pattern, header_text):
            return True
    
    return False

def extract_tables_from_file_improved(input_doc_path_str: str, output_csv_path_str: str | None = None):
    """
    Extract tables from a PDF file using improved pdfplumber logic
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
    else:
        _log.info(f"No output path provided. Using default output path.")
        output_dir = Path("scratch")
        output_csv_path = output_dir / f"{input_doc_path.stem}-improved.csv"

    output_dir.mkdir(parents=True, exist_ok=True)

    start_time = time.time()
    all_tables = []
    valid_table_count = 0

    try:
        with pdfplumber.open(input_doc_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                _log.info(f"Processing page {page_num + 1}")
                
                # Try different table extraction strategies
                tables = page.extract_tables(table_settings={
                    "vertical_strategy": "lines_strict",
                    "horizontal_strategy": "lines_strict",
                    "min_words_vertical": 3,
                    "min_words_horizontal": 3,
                })
                
                if not tables:
                    # Fallback: try with more lenient settings
                    tables = page.extract_tables(table_settings={
                        "vertical_strategy": "text",
                        "horizontal_strategy": "text",
                        "intersection_tolerance": 3,
                    })
                
                if tables:
                    for table_idx, table in enumerate(tables):
                        if is_valid_table(table):
                            cleaned_table = clean_table_data(table)
                            
                            if cleaned_table and len(cleaned_table) >= 2:
                                # Check if first row looks like headers
                                headers = cleaned_table[0]
                                data_rows = cleaned_table[1:]
                                
                                # Create DataFrame
                                df = pd.DataFrame(data_rows, columns=headers)
                                
                                # Remove completely empty columns
                                df = df.dropna(axis=1, how='all')
                                df = df.loc[:, (df != '').any(axis=0)]
                                
                                if not df.empty and len(df.columns) >= 2:
                                    all_tables.append(df)
                                    valid_table_count += 1
                                    _log.info(f"Extracted valid table {valid_table_count} from page {page_num + 1} "
                                            f"({len(df)} rows, {len(df.columns)} columns)")
                                    _log.info(f"Headers: {list(df.columns)}")
                        else:
                            _log.debug(f"Skipped invalid table {table_idx + 1} on page {page_num + 1}")
                            
    except Exception as e:
        _log.error(f"Error extracting tables: {e}")
        return []

    if not all_tables:
        _log.warning("No valid tables found in the PDF")
        return []

    # Function to sanitize DataFrame cells
    def sanitize_df_for_csv(df):
        # Clean string cells
        for col in df.columns:
            df[col] = df[col].astype(str).apply(lambda x: x.strip() if isinstance(x, str) else x)
        
        # Prevent CSV injection
        def prevent_csv_injection(val):
            if isinstance(val, str) and val.startswith(('.', '=', '+', '-', '@')):
                return "'" + val
            return val

        for col in df.columns:
            df[col] = df[col].apply(prevent_csv_injection)
        
        return df

    # Combine all tables into one CSV
    all_csv_parts = []
    
    for table_ix, table_df in enumerate(all_tables):
        sanitized_df = sanitize_df_for_csv(table_df.copy())
        
        # Convert to CSV
        csv_buffer = io.StringIO()
        # Include header only for the first table
        sanitized_df.to_csv(csv_buffer, index=False, header=(table_ix == 0))
        all_csv_parts.append(csv_buffer.getvalue())
        csv_buffer.close()
        _log.info(f"Added table {table_ix + 1} to CSV parts.")

    # Save combined CSV file
    if all_csv_parts:
        combined_csv_content = "".join(all_csv_parts)
        _log.info(f"Saving {len(all_tables)} tables to {output_csv_path}")
        with open(output_csv_path, 'w', encoding='utf-8') as f:
            f.write(combined_csv_content)
    else:
        _log.info("No valid tables found to create CSV file.")

    end_time = time.time() - start_time
    _log.info(f"Document processed in {end_time:.2f} seconds. Found {valid_table_count} valid tables.")
    
    return all_tables

if __name__ == "__main__":
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        output_path = sys.argv[2] if len(sys.argv) > 2 else None
        result = extract_tables_from_file_improved(file_path, output_path)
        print(f"Extracted {len(result)} tables")
    else:
        print("Usage: python pdftocsv_improved.py <input_pdf> [output_csv]")
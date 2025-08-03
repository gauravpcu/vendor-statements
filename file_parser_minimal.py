"""
Minimal file parser without OCR dependencies
"""
import logging
import pandas as pd
from pathlib import Path

logger = logging.getLogger(__name__)

def extract_headers(file_path, file_type=None, skip_rows=0):
    """Extract headers from file"""
    try:
        if file_path.endswith('.csv') or file_type == 'CSV':
            df = pd.read_csv(file_path, skiprows=skip_rows, nrows=0)
            return list(df.columns)
        elif file_path.endswith(('.xlsx', '.xls')) or file_type in ['XLSX', 'XLS']:
            df = pd.read_excel(file_path, skiprows=skip_rows, nrows=0)
            return list(df.columns)
        else:
            logger.warning(f"Unsupported file type for header extraction: {file_path}")
            return {"error": f"Unsupported file type: {file_type}"}
    except Exception as e:
        logger.error(f"Error extracting headers from {file_path}: {e}")
        return {"error": str(e)}

def extract_data(file_path, file_type, finalized_mappings, skip_rows=0, raw_pdf_table_content=None):
    """Extract data from file with field mappings"""
    try:
        # Read the data
        if file_path.endswith('.csv') or file_type == 'CSV':
            df = pd.read_csv(file_path, skiprows=skip_rows)
        elif file_path.endswith(('.xlsx', '.xls')) or file_type in ['XLSX', 'XLS']:
            df = pd.read_excel(file_path, skiprows=skip_rows)
        else:
            logger.warning(f"Unsupported file type for data extraction: {file_path}")
            return []
        
        # Apply field mappings if provided
        if finalized_mappings:
            # Create a mapping dictionary
            column_mapping = {}
            for mapping in finalized_mappings:
                original_header = mapping.get('original_header')
                mapped_field = mapping.get('mapped_field')
                if original_header and mapped_field and mapped_field != 'N/A':
                    column_mapping[original_header] = mapped_field
            
            # Rename columns based on mappings
            if column_mapping:
                df = df.rename(columns=column_mapping)
        
        # Convert to list of dictionaries (rows)
        return df.to_dict('records')
        
    except Exception as e:
        logger.error(f"Error extracting data from {file_path}: {e}")
        return []

def extract_headers_from_pdf_tables(tables):
    """Extract headers from PDF tables"""
    if not tables or len(tables) == 0:
        return []
    
    # Get headers from first table
    first_table = tables[0]
    if hasattr(first_table, 'columns'):
        return list(first_table.columns)
    else:
        return []
#!/usr/bin/env python3
"""
Invoice-specific PDF parser that extracts structured invoice line items
"""
import logging
import time
from pathlib import Path
import pandas as pd
import pdfplumber
import re

_log = logging.getLogger(__name__)

def extract_invoice_lines_from_text(text):
    """Extract structured invoice lines from text"""
    lines = text.split('\n')
    invoice_lines = []
    
    # Pattern for invoice lines: LINE_NUM DATE TYPE INVOICE_NUM [PO_NUM] AMOUNT [INVOICE_NUM AMOUNT]
    # Example: "1 04/04/25 INVOICE 858591183 197.75 858591183 197.75"
    # Example: "2 04/08/25 INVOICE 859068017 NHCA448397 116.99 859068017 116.99"
    
    invoice_pattern = r'^(\d+)\s+(\d{2}/\d{2}/\d{2,4})\s+(INVOICE|CREDIT MEMO)\s+(\d+)\s+(?:([A-Z0-9]+)\s+)?(-?\d+\.\d{2})\s+\d+\s+-?\d+\.\d{2}\s*$'
    
    for line in lines:
        line = line.strip()
        match = re.match(invoice_pattern, line)
        if match:
            line_num, date, doc_type, invoice_num, po_num, amount = match.groups()
            invoice_lines.append({
                'Line': line_num,
                'Date': date,
                'Type': doc_type,
                'Invoice_Number': invoice_num,
                'PO_Number': po_num or '',
                'Amount': float(amount)
            })
    
    return invoice_lines

def extract_invoice_data_from_pdf(input_doc_path_str: str, output_csv_path_str: str | None = None):
    """
    Extract invoice line items from PDF
    """
    logging.basicConfig(level=logging.INFO)
    
    input_doc_path = Path(input_doc_path_str)
    if not input_doc_path.is_file():
        _log.error(f"Input file not found: {input_doc_path}")
        return []

    # Determine output path
    if output_csv_path_str:
        output_csv_path = Path(output_csv_path_str)
    else:
        output_csv_path = Path("scratch") / f"{input_doc_path.stem}-invoice-lines.csv"
    
    output_csv_path.parent.mkdir(parents=True, exist_ok=True)

    start_time = time.time()
    all_invoice_lines = []

    try:
        with pdfplumber.open(input_doc_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                _log.info(f"Processing page {page_num + 1}")
                
                # Extract text from page
                text = page.extract_text()
                if text:
                    # Extract invoice lines from this page
                    page_lines = extract_invoice_lines_from_text(text)
                    all_invoice_lines.extend(page_lines)
                    _log.info(f"Found {len(page_lines)} invoice lines on page {page_num + 1}")
                    
    except Exception as e:
        _log.error(f"Error processing PDF: {e}")
        return []

    if not all_invoice_lines:
        _log.warning("No invoice lines found in PDF")
        return []

    # Create DataFrame
    df = pd.DataFrame(all_invoice_lines)
    
    # Sort by line number
    df = df.sort_values('Line').reset_index(drop=True)
    
    _log.info(f"Total invoice lines extracted: {len(df)}")
    _log.info(f"Columns: {list(df.columns)}")
    _log.info(f"Date range: {df['Date'].min()} to {df['Date'].max()}")
    _log.info(f"Amount range: ${df['Amount'].min():.2f} to ${df['Amount'].max():.2f}")
    _log.info(f"Total amount: ${df['Amount'].sum():.2f}")

    # Save to CSV
    df.to_csv(output_csv_path, index=False)
    _log.info(f"Saved invoice data to {output_csv_path}")

    end_time = time.time() - start_time
    _log.info(f"Processing completed in {end_time:.2f} seconds")
    
    return [df]  # Return as list to match expected format

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        output_path = sys.argv[2] if len(sys.argv) > 2 else None
        result = extract_invoice_data_from_pdf(file_path, output_path)
        if result:
            print(f"✅ Successfully extracted {len(result[0])} invoice lines")
            print(f"📊 Sample data:")
            print(result[0].head())
        else:
            print("❌ No data extracted")
    else:
        print("Usage: python pdftocsv_invoice.py <input_pdf> [output_csv]")
#!/usr/bin/env python3
"""
Analyze the PDF structure to understand what we're dealing with
"""
import pdfplumber
import re

def analyze_pdf_structure(pdf_path):
    """Analyze PDF to understand its structure"""
    print(f"🔍 Analyzing PDF: {pdf_path}")
    print("=" * 60)
    
    with pdfplumber.open(pdf_path) as pdf:
        print(f"📄 Total pages: {len(pdf.pages)}")
        
        # Analyze first page in detail
        page = pdf.pages[0]
        print(f"\n📊 Page 1 Analysis:")
        print(f"  - Page size: {page.width} x {page.height}")
        
        # Extract all text
        text = page.extract_text()
        print(f"  - Text length: {len(text)} characters")
        
        # Look for table-like patterns
        lines = text.split('\n')
        print(f"  - Text lines: {len(lines)}")
        
        print(f"\n📝 First 20 lines of text:")
        for i, line in enumerate(lines[:20]):
            print(f"  {i+1:2d}: {repr(line)}")
        
        # Look for patterns that might be invoice lines
        invoice_patterns = [
            r'\d{2}/\d{2}/\d{2,4}',  # Dates
            r'\d+\.\d{2}',           # Amounts
            r'INVOICE',              # Invoice keyword
            r'\d{8,}',               # Long numbers (invoice numbers)
        ]
        
        print(f"\n🔍 Pattern Analysis:")
        for pattern in invoice_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            print(f"  - {pattern}: {len(matches)} matches")
            if matches:
                print(f"    Examples: {matches[:5]}")
        
        # Try to extract tables
        tables = page.extract_tables()
        print(f"\n📋 Table extraction:")
        print(f"  - Tables found: {len(tables)}")
        
        if tables:
            for i, table in enumerate(tables[:3]):  # Show first 3 tables
                print(f"\n  Table {i+1}:")
                print(f"    - Rows: {len(table)}")
                print(f"    - Columns: {len(table[0]) if table else 0}")
                if table:
                    print(f"    - First row: {table[0]}")
                    if len(table) > 1:
                        print(f"    - Second row: {table[1]}")
        
        # Look for structured data patterns
        print(f"\n🎯 Looking for structured data patterns:")
        
        # Check if there are lines that look like invoice items
        invoice_line_pattern = r'^\s*\d+\s+\d{2}/\d{2}/\d{2,4}\s+.*?\s+\d+\.\d{2}\s*$'
        invoice_lines = []
        for line in lines:
            if re.match(invoice_line_pattern, line):
                invoice_lines.append(line)
        
        print(f"  - Potential invoice lines: {len(invoice_lines)}")
        if invoice_lines:
            print(f"    Examples:")
            for line in invoice_lines[:3]:
                print(f"      {repr(line)}")

if __name__ == "__main__":
    pdf_path = "uploads/HDSupply.pdf"
    analyze_pdf_structure(pdf_path)
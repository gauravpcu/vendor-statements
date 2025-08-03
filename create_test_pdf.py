#!/usr/bin/env python3
"""
Create a simple test PDF with a table for testing
"""
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
    from reportlab.lib import colors
    
    def create_test_pdf():
        """Create a simple PDF with a table"""
        filename = "test.pdf"
        
        # Create document
        doc = SimpleDocTemplate(filename, pagesize=letter)
        
        # Sample data for table
        data = [
            ['Invoice #', 'Date', 'Vendor', 'Amount'],
            ['INV-001', '2025-01-01', 'Acme Corp', '$1,000.00'],
            ['INV-002', '2025-01-02', 'Beta LLC', '$2,500.00'],
            ['INV-003', '2025-01-03', 'Gamma Inc', '$750.00'],
        ]
        
        # Create table
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        # Build PDF
        doc.build([table])
        print(f"✅ Created test PDF: {filename}")
        return filename
    
    if __name__ == "__main__":
        create_test_pdf()
        
except ImportError:
    print("⚠️  reportlab not installed. Creating a simple text-based test instead.")
    
    def create_simple_test():
        """Create a simple text file that can be used for testing"""
        filename = "test_data.csv"
        with open(filename, 'w') as f:
            f.write("Invoice #,Date,Vendor,Amount\n")
            f.write("INV-001,2025-01-01,Acme Corp,$1000.00\n")
            f.write("INV-002,2025-01-02,Beta LLC,$2500.00\n")
            f.write("INV-003,2025-01-03,Gamma Inc,$750.00\n")
        print(f"✅ Created test CSV: {filename}")
        return filename
    
    if __name__ == "__main__":
        create_simple_test()
#!/usr/bin/env python3
"""
Simulate the actual upload process to test template auto-application.
"""

import os
import json
import tempfile
import csv
from io import StringIO

def create_test_csv_file(filename, headers, data_rows):
    """Create a test CSV file with given headers and data."""
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        # Add some empty rows to test skip_rows functionality
        if "Basic" in filename:
            # Basic template has skip_rows: 10
            for i in range(10):
                writer.writerow([f"Skip row {i+1}", "", "", ""])
        elif "Alpha-Med-WithHeaders" in filename:
            # Alpha-Med-WithHeaders has skip_rows: 4
            for i in range(4):
                writer.writerow([f"Header row {i+1}", "", "", ""])
        
        # Write actual headers
        writer.writerow(headers)
        
        # Write data rows
        for row in data_rows:
            writer.writerow(row)

def simulate_upload_process():
    """Simulate the upload process with template auto-application."""
    
    print("🧪 Simulating Upload Process with Template Auto-Application")
    print("=" * 60)
    
    # Test cases with different filename patterns
    test_cases = [
        {
            "filename": "Basic_invoice_2024.csv",
            "headers": ["Purchase Order Number", "Inv Ref", "Doc Date", "Amount", "Tax"],
            "data": [
                ["PO-001", "INV-001", "2024-01-15", "1000.00", "100.00"],
                ["PO-002", "INV-002", "2024-01-16", "2000.00", "200.00"]
            ]
        },
        {
            "filename": "NHCA_report.csv", 
            "headers": ["DATE T", "INVOICE", "VENDOR", "AMOUNT"],
            "data": [
                ["2024-01-15", "INV-001", "Vendor A", "1500.00"],
                ["2024-01-16", "INV-002", "Vendor B", "2500.00"]
            ]
        },
        {
            "filename": "Alpha-Med_statement.csv",
            "headers": ["Account set", "Invoice Number", "Date", "Total"],
            "data": [
                ["ACC-001", "INV-001", "2024-01-15", "3000.00"],
                ["ACC-002", "INV-002", "2024-01-16", "4000.00"]
            ]
        }
    ]
    
    for test_case in test_cases:
        print(f"\n📄 Testing: {test_case['filename']}")
        print("-" * 40)
        
        # Create temporary test file
        temp_file = os.path.join("uploads", test_case['filename'])
        os.makedirs("uploads", exist_ok=True)
        
        try:
            create_test_csv_file(temp_file, test_case['headers'], test_case['data'])
            print(f"✅ Created test file: {temp_file}")
            
            # Simulate the template matching logic from app.py
            original_filename_for_vendor = test_case['filename']
            template_applied_data = None
            TEMPLATES_DIR = "templates_storage"
            
            # Extract template name
            template_name_from_file = ""
            if original_filename_for_vendor:
                name_without_extension = os.path.splitext(original_filename_for_vendor)[0]
                import re
                parts = re.split(r'[ _-]', name_without_extension, 1)
                if parts: 
                    template_name_from_file = parts[0]
                    print(f"🎯 Extracted template name: '{template_name_from_file}'")
            
            # Search for template
            if template_name_from_file and os.path.exists(TEMPLATES_DIR):
                normalized_template_name = template_name_from_file.lower()
                template_files = [f for f in os.listdir(TEMPLATES_DIR) if f.endswith(".json")]
                template_files.sort(key=lambda x: len(os.path.splitext(x)[0]), reverse=True)
                
                for template_file_in_storage in template_files:
                    template_base_name = os.path.splitext(template_file_in_storage)[0]
                    template_base_name_lower = template_base_name.lower()
                    
                    is_exact_match = template_base_name_lower == normalized_template_name
                    is_prefix_match = template_base_name_lower.startswith(normalized_template_name + "-") or \
                                    normalized_template_name.startswith(template_base_name_lower)
                    
                    if is_exact_match or is_prefix_match:
                        template_path = os.path.join(TEMPLATES_DIR, template_file_in_storage)
                        with open(template_path, 'r', encoding='utf-8') as f_tpl:
                            loaded_template = json.load(f_tpl)
                        
                        if "field_mappings" in loaded_template:
                            template_applied_data = loaded_template
                            skip_rows = loaded_template.get("skip_rows", 0)
                            template_name = loaded_template.get("template_name", template_base_name)
                            
                            match_type = "exact" if is_exact_match else "prefix"
                            print(f"🎯 Template '{template_name}' auto-applied ({match_type} match) with {skip_rows} skip rows")
                            
                            # Show field mappings
                            field_mappings = loaded_template.get("field_mappings", [])
                            print(f"📋 Field mappings ({len(field_mappings)}):")
                            for mapping in field_mappings[:3]:  # Show first 3
                                print(f"   - '{mapping['original_header']}' → {mapping['mapped_field']}")
                            if len(field_mappings) > 3:
                                print(f"   - ... and {len(field_mappings) - 3} more")
                            break
            
            if not template_applied_data:
                print(f"❌ No template found for '{template_name_from_file}'")
                print("🤖 Would use AI mapping instead")
            
            # Simulate header extraction with skip_rows
            print(f"\n📊 File Analysis:")
            with open(temp_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                print(f"   - Total lines: {len(lines)}")
                
                if template_applied_data:
                    skip_rows = template_applied_data.get("skip_rows", 0)
                    if skip_rows > 0:
                        print(f"   - Skipping first {skip_rows} rows")
                        if skip_rows < len(lines):
                            header_line = lines[skip_rows].strip()
                            print(f"   - Header line: {header_line}")
                        else:
                            print(f"   - ⚠️  Skip rows ({skip_rows}) exceeds file length!")
                    else:
                        header_line = lines[0].strip() if lines else ""
                        print(f"   - Header line: {header_line}")
                else:
                    header_line = lines[0].strip() if lines else ""
                    print(f"   - Header line: {header_line}")
            
        except Exception as e:
            print(f"❌ Error processing {test_case['filename']}: {e}")
        
        finally:
            # Clean up
            if os.path.exists(temp_file):
                os.remove(temp_file)
    
    # Clean up uploads directory if empty
    try:
        os.rmdir("uploads")
    except:
        pass

def test_actual_flask_endpoint():
    """Test the actual Flask endpoint if possible."""
    print(f"\n🌐 Testing Actual Flask Endpoint:")
    print("-" * 35)
    
    try:
        import requests
        
        # Test with a simple file upload
        test_url = "http://localhost:5000/upload"  # Local Flask server
        
        # Create a simple test file
        test_content = "Purchase Order Number,Inv Ref,Doc Date,Amount\\nPO-001,INV-001,2024-01-15,1000.00"
        
        files = {'files[]': ('Basic_test.csv', test_content, 'text/csv')}
        
        print(f"📤 Attempting upload to {test_url}")
        response = requests.post(test_url, files=files, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Upload successful!")
            
            if isinstance(result, list) and len(result) > 0:
                file_result = result[0]
                if file_result.get('applied_template_name'):
                    print(f"🎯 Template applied: {file_result['applied_template_name']}")
                    print(f"📝 Message: {file_result.get('message', 'No message')}")
                else:
                    print("❌ No template was applied")
                    print(f"📝 Message: {file_result.get('message', 'No message')}")
            else:
                print("⚠️  Unexpected response format")
        else:
            print(f"❌ Upload failed: {response.status_code}")
            
    except ImportError:
        print("⚠️  requests library not available")
    except Exception as e:
        print(f"❌ Error testing Flask endpoint: {e}")
        print("💡 Make sure Flask server is running on localhost:5000")

if __name__ == "__main__":
    simulate_upload_process()
    test_actual_flask_endpoint()
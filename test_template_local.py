#!/usr/bin/env python3
"""
Local test script to debug template auto-application functionality.
"""

import os
import json
import re
from datetime import datetime

# Simulate the constants from app.py
TEMPLATES_DIR = "templates_storage"

def test_template_extraction_and_matching():
    """Test the template extraction and matching logic locally."""
    
    print("🧪 Testing Template Auto-Application Logic Locally")
    print("=" * 55)
    
    # Check if templates directory exists
    if not os.path.exists(TEMPLATES_DIR):
        print(f"❌ Templates directory '{TEMPLATES_DIR}' not found!")
        return
    
    # Get available templates
    template_files = [f for f in os.listdir(TEMPLATES_DIR) if f.endswith(".json")]
    template_files.sort(key=lambda x: len(os.path.splitext(x)[0]), reverse=True)
    
    print(f"📁 Available templates: {[os.path.splitext(f)[0] for f in template_files]}")
    print()
    
    # Test various filename patterns
    test_filenames = [
        "Basic_invoice_2024.pdf",
        "basic-statement.xlsx", 
        "NHCA_report.csv",
        "nhca-data.pdf",
        "Alpha-Med_invoice.xlsx",
        "alpha-med-statement.pdf",
        "Unknown_vendor.csv",
        "random_file.pdf",
        "Basic.xlsx",
        "NHCA.pdf",
        "Alpha-Med-WithHeaders_test.csv"
    ]
    
    print("🔍 Testing Template Matching Logic:")
    print("-" * 40)
    
    for original_filename_for_vendor in test_filenames:
        print(f"\n📄 Testing: {original_filename_for_vendor}")
        
        # Step 1: Extract Template Name (same logic as app.py)
        template_name_from_file = ""
        template_applied_data = None
        
        if original_filename_for_vendor:
            name_without_extension = os.path.splitext(original_filename_for_vendor)[0]
            # Split by the first occurrence of space, underscore, or hyphen
            parts = re.split(r'[ _-]', name_without_extension, 1)
            if parts: 
                template_name_from_file = parts[0]
                print(f"   🎯 Extracted template name: '{template_name_from_file}'")
        
        # Step 2: Search for matching template
        if template_name_from_file and os.path.exists(TEMPLATES_DIR):
            print(f"   🔍 Searching for template matching: '{template_name_from_file}'")
            normalized_template_name = template_name_from_file.lower()
            
            for template_file_in_storage in template_files:
                template_base_name = os.path.splitext(template_file_in_storage)[0]
                template_base_name_lower = template_base_name.lower()
                
                # Enhanced matching: exact match or starts with
                is_exact_match = template_base_name_lower == normalized_template_name
                is_prefix_match = template_base_name_lower.startswith(normalized_template_name + "-") or \
                                normalized_template_name.startswith(template_base_name_lower)
                
                print(f"      📋 Checking '{template_base_name}' (lower: '{template_base_name_lower}')")
                print(f"         - Exact match: {is_exact_match}")
                print(f"         - Prefix match: {is_prefix_match}")
                
                if is_exact_match or is_prefix_match:
                    try:
                        template_path = os.path.join(TEMPLATES_DIR, template_file_in_storage)
                        with open(template_path, 'r', encoding='utf-8') as f_tpl:
                            loaded_template = json.load(f_tpl)
                        
                        if "field_mappings" in loaded_template:
                            template_applied_data = loaded_template
                            skip_rows = loaded_template.get("skip_rows", 0)
                            template_name = loaded_template.get("template_name", template_base_name)
                            field_count = len(loaded_template.get("field_mappings", []))
                            
                            match_type = "exact" if is_exact_match else "prefix"
                            print(f"   ✅ MATCH FOUND: '{template_file_in_storage}' ({match_type})")
                            print(f"      - Template name: {template_name}")
                            print(f"      - Skip rows: {skip_rows}")
                            print(f"      - Field mappings: {field_count}")
                            break
                            
                    except Exception as e:
                        print(f"   ❌ Error loading template {template_file_in_storage}: {e}")
            
            if not template_applied_data:
                print(f"   ❌ No template found for '{template_name_from_file}'")
        else:
            if not template_name_from_file:
                print("   ⚠️  No template name extracted from filename")
            else:
                print(f"   ❌ Templates directory '{TEMPLATES_DIR}' not found")
    
    print("\n" + "=" * 55)
    print("🔧 Debugging Tips:")
    print("1. Check if templates directory exists and has .json files")
    print("2. Verify template files have 'field_mappings' key")
    print("3. Ensure filename starts with template name (case-insensitive)")
    print("4. Template matching supports exact and prefix matches")

def test_specific_template_loading():
    """Test loading a specific template to verify structure."""
    print("\n📋 Testing Template Loading:")
    print("-" * 30)
    
    if not os.path.exists(TEMPLATES_DIR):
        print(f"❌ Templates directory '{TEMPLATES_DIR}' not found!")
        return
    
    template_files = [f for f in os.listdir(TEMPLATES_DIR) if f.endswith(".json")]
    
    for template_file in template_files:
        template_path = os.path.join(TEMPLATES_DIR, template_file)
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template_data = json.load(f)
            
            template_name = template_data.get('template_name', 'Unknown')
            skip_rows = template_data.get('skip_rows', 0)
            field_mappings = template_data.get('field_mappings', [])
            
            print(f"✅ {template_file}:")
            print(f"   - Name: {template_name}")
            print(f"   - Skip rows: {skip_rows}")
            print(f"   - Field mappings: {len(field_mappings)}")
            
            if field_mappings:
                print(f"   - Sample mapping: {field_mappings[0]}")
            
        except Exception as e:
            print(f"❌ Error loading {template_file}: {e}")

if __name__ == "__main__":
    test_template_extraction_and_matching()
    test_specific_template_loading()
#!/usr/bin/env python3
"""
Debug template auto-application by testing the exact logic from app.py
"""

import os
import json
import re
import tempfile
import csv

# Constants from app.py
TEMPLATES_DIR = "templates_storage"

def test_template_logic_step_by_step():
    """Test each step of the template logic to find where it might be failing."""
    
    print("🔍 Step-by-Step Template Logic Debug")
    print("=" * 40)
    
    # Test filename
    original_filename_for_vendor = "Basic_invoice_2024.pdf"
    print(f"📄 Testing filename: {original_filename_for_vendor}")
    
    # Step 1: Extract Template Name (Enhanced Logic)
    template_name_from_file = ""
    if original_filename_for_vendor:
        name_without_extension = os.path.splitext(original_filename_for_vendor)[0]
        print(f"   Name without extension: '{name_without_extension}'")
        
        # Split by the first occurrence of space, underscore, or hyphen
        parts = re.split(r'[ _-]', name_without_extension, 1)
        print(f"   Split parts: {parts}")
        
        if parts: 
            template_name_from_file = parts[0]
            print(f"   ✅ Extracted template name: '{template_name_from_file}'")
    
    # Step 2: Check if templates directory exists
    print(f"\n🔍 Checking templates directory: {TEMPLATES_DIR}")
    if os.path.exists(TEMPLATES_DIR):
        print(f"   ✅ Templates directory exists")
        
        # List all files
        all_files = os.listdir(TEMPLATES_DIR)
        print(f"   📁 All files: {all_files}")
        
        # Filter JSON files
        template_files = [f for f in all_files if f.endswith(".json")]
        print(f"   📄 JSON files: {template_files}")
        
        # Sort by specificity
        template_files.sort(key=lambda x: len(os.path.splitext(x)[0]), reverse=True)
        print(f"   📋 Sorted templates: {template_files}")
        
    else:
        print(f"   ❌ Templates directory does not exist!")
        return
    
    # Step 3: Enhanced Template Search and Auto-Apply Logic
    template_applied_data = None
    if template_name_from_file and os.path.exists(TEMPLATES_DIR):
        print(f"\n🔍 Searching for template matching: '{template_name_from_file}'")
        normalized_template_name = template_name_from_file.lower()
        print(f"   Normalized name: '{normalized_template_name}'")
        
        for template_file_in_storage in template_files:
            template_base_name = os.path.splitext(template_file_in_storage)[0]
            template_base_name_lower = template_base_name.lower()
            
            print(f"\\n   🔍 Checking template: {template_file_in_storage}")
            print(f"      Base name: '{template_base_name}'")
            print(f"      Lower case: '{template_base_name_lower}'")
            
            # Enhanced matching: exact match or starts with
            is_exact_match = template_base_name_lower == normalized_template_name
            is_prefix_match = template_base_name_lower.startswith(normalized_template_name + "-") or \
                            normalized_template_name.startswith(template_base_name_lower)
            
            print(f"      Exact match: {is_exact_match}")
            print(f"      Prefix match: {is_prefix_match}")
            
            if is_exact_match or is_prefix_match:
                print(f"      ✅ MATCH FOUND!")
                
                try:
                    template_path = os.path.join(TEMPLATES_DIR, template_file_in_storage)
                    print(f"      📂 Loading template from: {template_path}")
                    
                    with open(template_path, 'r', encoding='utf-8') as f_tpl:
                        loaded_template = json.load(f_tpl)
                    
                    print(f"      📋 Template keys: {list(loaded_template.keys())}")
                    
                    if "field_mappings" in loaded_template: # Basic validation
                        template_applied_data = loaded_template
                        current_skip_rows_for_extraction = loaded_template.get("skip_rows", 0)
                        
                        # Simulate results_entry updates
                        applied_template_name = loaded_template.get("template_name", template_base_name)
                        applied_template_filename = template_file_in_storage
                        
                        match_type = "exact" if is_exact_match else "prefix"
                        print(f"      🎯 Template '{applied_template_name}' would be auto-applied ({match_type} match)")
                        print(f"      📊 Skip rows: {current_skip_rows_for_extraction}")
                        print(f"      📋 Field mappings: {len(loaded_template.get('field_mappings', []))}")
                        
                        # Show what the success message would be
                        success_message = f"🎯 Template '{applied_template_name}' auto-applied (matched first word '{template_name_from_file}') with {current_skip_rows_for_extraction} skip rows."
                        print(f"      💬 Success message: {success_message}")
                        
                        break # Stop searching once a template is found
                    else:
                        print(f"      ❌ Template missing 'field_mappings' key")
                        
                except Exception as e_tpl_load:
                    print(f"      ❌ Error loading template {template_file_in_storage}: {e_tpl_load}")
        
        if not template_applied_data:
            print(f"\\n   ❌ No template found for '{template_name_from_file}'")
            available_templates = [os.path.splitext(f)[0] for f in template_files]
            print(f"   📋 Available templates: {available_templates}")
    else:
        if not template_name_from_file:
            print(f"\\n   ❌ No template name extracted from filename")
        else:
            print(f"\\n   ❌ Templates directory not found")
    
    return template_applied_data is not None

def test_multiple_filenames():
    """Test multiple filename patterns."""
    
    print("\\n\\n🧪 Testing Multiple Filename Patterns")
    print("=" * 45)
    
    test_filenames = [
        "Basic_invoice_2024.pdf",
        "basic-statement.xlsx", 
        "NHCA_report.csv",
        "Alpha-Med_invoice.xlsx",
        "Unknown_vendor.csv",
        "Basic.xlsx",
        "NHCA.pdf"
    ]
    
    results = []
    
    for filename in test_filenames:
        print(f"\\n📄 Testing: {filename}")
        
        # Extract template name
        template_name_from_file = ""
        if filename:
            name_without_extension = os.path.splitext(filename)[0]
            parts = re.split(r'[ _-]', name_without_extension, 1)
            if parts: 
                template_name_from_file = parts[0]
        
        # Check for template match
        template_found = False
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
                    try:
                        template_path = os.path.join(TEMPLATES_DIR, template_file_in_storage)
                        with open(template_path, 'r', encoding='utf-8') as f_tpl:
                            loaded_template = json.load(f_tpl)
                        
                        if "field_mappings" in loaded_template:
                            template_found = True
                            match_type = "exact" if is_exact_match else "prefix"
                            template_name = loaded_template.get("template_name", template_base_name)
                            skip_rows = loaded_template.get("skip_rows", 0)
                            
                            print(f"   ✅ {template_name} ({match_type}) - skip {skip_rows} rows")
                            break
                    except:
                        pass
        
        if not template_found:
            print(f"   ❌ No template match")
        
        results.append({
            'filename': filename,
            'template_name': template_name_from_file,
            'found': template_found
        })
    
    print(f"\\n📊 Summary:")
    success_count = sum(1 for r in results if r['found'])
    print(f"   ✅ Templates found: {success_count}/{len(results)}")
    print(f"   ❌ No template: {len(results) - success_count}/{len(results)}")

if __name__ == "__main__":
    # Test the detailed logic
    success = test_template_logic_step_by_step()
    
    # Test multiple patterns
    test_multiple_filenames()
    
    print(f"\\n🎯 Overall Result: {'✅ Template logic working' if success else '❌ Template logic failed'}")
    
    if success:
        print("\\n💡 If templates aren't working in the web app, check:")
        print("   1. Are the templates being copied to the Docker container?")
        print("   2. Is the TEMPLATES_DIR path correct in the container?")
        print("   3. Are there any errors in the Flask application logs?")
        print("   4. Is the template matching code being executed?")
    else:
        print("\\n💡 Template logic has issues that need to be fixed locally first.")
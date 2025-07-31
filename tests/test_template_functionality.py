#!/usr/bin/env python3
"""
Test script to verify template functionality is working correctly.
"""

import json
import os
import sys

def test_template_files():
    """Test that template files exist and are valid JSON."""
    templates_dir = "templates_storage"
    
    if not os.path.exists(templates_dir):
        print(f"❌ Templates directory '{templates_dir}' does not exist")
        return False
    
    template_files = [f for f in os.listdir(templates_dir) if f.endswith('.json')]
    
    if not template_files:
        print(f"❌ No template files found in '{templates_dir}'")
        return False
    
    print(f"✅ Found {len(template_files)} template files:")
    
    for template_file in template_files:
        template_path = os.path.join(templates_dir, template_file)
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template_data = json.load(f)
            
            # Validate template structure
            required_fields = ['template_name', 'field_mappings', 'skip_rows']
            missing_fields = [field for field in required_fields if field not in template_data]
            
            if missing_fields:
                print(f"  ❌ {template_file}: Missing fields: {missing_fields}")
                return False
            else:
                print(f"  ✅ {template_file}: Valid template with {len(template_data['field_mappings'])} mappings, skip_rows={template_data['skip_rows']}")
        
        except json.JSONDecodeError as e:
            print(f"  ❌ {template_file}: Invalid JSON - {e}")
            return False
        except Exception as e:
            print(f"  ❌ {template_file}: Error reading file - {e}")
            return False
    
    return True

def test_field_definitions():
    """Test that field definitions file exists and is valid."""
    field_def_file = "field_definitions.json"
    
    if not os.path.exists(field_def_file):
        print(f"❌ Field definitions file '{field_def_file}' does not exist")
        return False
    
    try:
        with open(field_def_file, 'r', encoding='utf-8') as f:
            field_definitions = json.load(f)
        
        if not field_definitions:
            print(f"❌ Field definitions file is empty")
            return False
        
        print(f"✅ Field definitions loaded successfully with {len(field_definitions)} fields:")
        for field_key, field_data in list(field_definitions.items())[:5]:  # Show first 5
            display_name = field_data.get('display_name', field_key) if isinstance(field_data, dict) else field_key
            print(f"  - {field_key}: {display_name}")
        
        if len(field_definitions) > 5:
            print(f"  ... and {len(field_definitions) - 5} more")
        
        return True
    
    except json.JSONDecodeError as e:
        print(f"❌ Field definitions file has invalid JSON - {e}")
        return False
    except Exception as e:
        print(f"❌ Error reading field definitions file - {e}")
        return False

def test_app_routes():
    """Test that the app file contains the required routes."""
    app_file = "app.py"
    
    if not os.path.exists(app_file):
        print(f"❌ App file '{app_file}' does not exist")
        return False
    
    try:
        with open(app_file, 'r', encoding='utf-8') as f:
            app_content = f.read()
        
        required_routes = [
            '/apply_template',
            '/list_templates',
            '/get_template_details',
            '/save_template',
            '/delete_template',
            '/field_definitions'
        ]
        
        missing_routes = []
        for route in required_routes:
            if route not in app_content:
                missing_routes.append(route)
        
        if missing_routes:
            print(f"❌ Missing routes in app.py: {missing_routes}")
            return False
        else:
            print(f"✅ All required routes found in app.py: {required_routes}")
            return True
    
    except Exception as e:
        print(f"❌ Error reading app.py - {e}")
        return False

def test_frontend_files():
    """Test that frontend files exist."""
    required_files = [
        "templates/manage_templates.html",
        "static/js/manage_templates.js",
        "static/js/upload.js",
        "templates/index.html"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing frontend files: {missing_files}")
        return False
    else:
        print(f"✅ All required frontend files exist")
        return True

def main():
    """Run all tests."""
    print("🧪 Testing Template Functionality Implementation")
    print("=" * 50)
    
    tests = [
        ("Template Files", test_template_files),
        ("Field Definitions", test_field_definitions),
        ("App Routes", test_app_routes),
        ("Frontend Files", test_frontend_files)
    ]
    
    all_passed = True
    
    for test_name, test_func in tests:
        print(f"\n📋 Testing {test_name}:")
        if not test_func():
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All tests passed! Template functionality should be working correctly.")
        print("\n📝 Next steps:")
        print("1. Start the Flask app: source .venv/bin/activate && python app.py")
        print("2. Open http://localhost:5000 in your browser")
        print("3. Try uploading a file and applying a template")
        print("4. Go to 'Manage Saved Templates' to create new templates")
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
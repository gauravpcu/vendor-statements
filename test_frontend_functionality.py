#!/usr/bin/env python3
"""
Test script to verify frontend template functionality by checking file contents.
"""

import os
import json
import re

def test_frontend_template_functionality():
    """Test that frontend files contain the expected template functionality."""
    print("🧪 Testing Frontend Template Functionality")
    print("=" * 50)
    
    tests_passed = 0
    total_tests = 0
    
    # Test 1: Check upload.js has enhanced applyTemplate function
    print("📋 Testing upload.js enhancements:")
    total_tests += 1
    
    try:
        with open('static/js/upload.js', 'r') as f:
            upload_js_content = f.read()
        
        # Check for key functionality
        checks = [
            ('apply_template route usage', '/apply_template' in upload_js_content),
            ('renderMappingTable call', 'renderMappingTable(' in upload_js_content),
            ('template application logic', 'applyTemplate(' in upload_js_content),
            ('error handling', 'catch(error' in upload_js_content),
        ]
        
        all_checks_passed = all(check[1] for check in checks)
        
        if all_checks_passed:
            tests_passed += 1
            print("   ✅ upload.js has all required template functionality")
            for check_name, passed in checks:
                print(f"      ✅ {check_name}")
        else:
            print("   ❌ upload.js missing some functionality:")
            for check_name, passed in checks:
                status = "✅" if passed else "❌"
                print(f"      {status} {check_name}")
    
    except FileNotFoundError:
        print("   ❌ upload.js file not found")
    except Exception as e:
        print(f"   ❌ Error reading upload.js: {e}")
    
    # Test 2: Check manage_templates.html has creation modal
    print("\n📋 Testing manage_templates.html enhancements:")
    total_tests += 1
    
    try:
        with open('templates/manage_templates.html', 'r') as f:
            html_content = f.read()
        
        # Check for key elements
        checks = [
            ('Create New Template button', 'createNewTemplateBtn' in html_content),
            ('Template creation modal', 'createTemplateModal' in html_content),
            ('Field mappings container', 'fieldMappingsContainer' in html_content),
            ('Form elements', 'createTemplateForm' in html_content),
        ]
        
        all_checks_passed = all(check[1] for check in checks)
        
        if all_checks_passed:
            tests_passed += 1
            print("   ✅ manage_templates.html has all required elements")
            for check_name, passed in checks:
                print(f"      ✅ {check_name}")
        else:
            print("   ❌ manage_templates.html missing some elements:")
            for check_name, passed in checks:
                status = "✅" if passed else "❌"
                print(f"      {status} {check_name}")
    
    except FileNotFoundError:
        print("   ❌ manage_templates.html file not found")
    except Exception as e:
        print(f"   ❌ Error reading manage_templates.html: {e}")
    
    # Test 3: Check manage_templates.js has creation functionality
    print("\n📋 Testing manage_templates.js enhancements:")
    total_tests += 1
    
    try:
        with open('static/js/manage_templates.js', 'r') as f:
            js_content = f.read()
        
        # Check for key functionality
        checks = [
            ('Template creation form handling', 'createTemplateForm' in js_content),
            ('Field definitions loading', 'field_definitions' in js_content or 'fieldDefinitions' in js_content),
            ('Dynamic mapping rows', 'addMappingBtn' in js_content),
            ('Template saving', '/save_template' in js_content),
            ('Template deletion', 'delete-template-btn' in js_content),
        ]
        
        all_checks_passed = all(check[1] for check in checks)
        
        if all_checks_passed:
            tests_passed += 1
            print("   ✅ manage_templates.js has all required functionality")
            for check_name, passed in checks:
                print(f"      ✅ {check_name}")
        else:
            print("   ❌ manage_templates.js missing some functionality:")
            for check_name, passed in checks:
                status = "✅" if passed else "❌"
                print(f"      {status} {check_name}")
    
    except FileNotFoundError:
        print("   ❌ manage_templates.js file not found")
    except Exception as e:
        print(f"   ❌ Error reading manage_templates.js: {e}")
    
    # Test 4: Check template files are valid and have expected structure
    print("\n📋 Testing template file structure:")
    total_tests += 1
    
    try:
        templates_dir = "templates_storage"
        template_files = [f for f in os.listdir(templates_dir) if f.endswith('.json')]
        
        if not template_files:
            print("   ❌ No template files found")
        else:
            valid_templates = 0
            for template_file in template_files:
                template_path = os.path.join(templates_dir, template_file)
                try:
                    with open(template_path, 'r') as f:
                        template_data = json.load(f)
                    
                    # Check required fields
                    required_fields = ['template_name', 'field_mappings', 'skip_rows']
                    has_all_fields = all(field in template_data for field in required_fields)
                    
                    if has_all_fields:
                        valid_templates += 1
                        print(f"      ✅ {template_file}: Valid structure")
                    else:
                        missing = [f for f in required_fields if f not in template_data]
                        print(f"      ❌ {template_file}: Missing fields: {missing}")
                
                except json.JSONDecodeError:
                    print(f"      ❌ {template_file}: Invalid JSON")
                except Exception as e:
                    print(f"      ❌ {template_file}: Error reading - {e}")
            
            if valid_templates == len(template_files):
                tests_passed += 1
                print(f"   ✅ All {valid_templates} template files are valid")
            else:
                print(f"   ❌ Only {valid_templates}/{len(template_files)} template files are valid")
    
    except FileNotFoundError:
        print("   ❌ Templates directory not found")
    except Exception as e:
        print(f"   ❌ Error checking templates: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Frontend Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All frontend functionality is properly implemented!")
        print("\n✅ Frontend features verified:")
        print("  - Enhanced template application in upload.js")
        print("  - Template creation modal in manage_templates.html")
        print("  - Template management functionality in manage_templates.js")
        print("  - Valid template file structures")
        print("\n🌐 Ready for testing:")
        print("  1. Start the Flask app: source .venv/bin/activate && python app.py")
        print("  2. Open http://127.0.0.1:8080 in your browser")
        print("  3. Test file upload with template auto-application")
        print("  4. Test manual template application")
        print("  5. Test template creation and management")
    else:
        print(f"❌ {total_tests - tests_passed} frontend tests failed.")
        return False
    
    return True

if __name__ == "__main__":
    success = test_frontend_template_functionality()
    if not success:
        exit(1)
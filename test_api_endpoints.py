#!/usr/bin/env python3
"""
Test script to verify all template API endpoints are working correctly.
"""

import requests
import json
import sys

BASE_URL = "http://127.0.0.1:8080"

def test_endpoint(method, endpoint, data=None, files=None, expected_status=200):
    """Test a single API endpoint."""
    url = f"{BASE_URL}{endpoint}"
    
    try:
        if method.upper() == "GET":
            response = requests.get(url)
        elif method.upper() == "POST":
            if files:
                response = requests.post(url, data=data, files=files)
            elif data:
                response = requests.post(url, json=data)
            else:
                response = requests.post(url)
        elif method.upper() == "DELETE":
            response = requests.delete(url)
        else:
            print(f"❌ Unsupported method: {method}")
            return False
        
        if response.status_code == expected_status:
            print(f"✅ {method} {endpoint} - Status: {response.status_code}")
            return True, response.json() if response.content else {}
        else:
            print(f"❌ {method} {endpoint} - Expected: {expected_status}, Got: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            return False, {}
    
    except requests.exceptions.ConnectionError:
        print(f"❌ {method} {endpoint} - Connection failed. Is the server running on {BASE_URL}?")
        return False, {}
    except Exception as e:
        print(f"❌ {method} {endpoint} - Error: {e}")
        return False, {}

def main():
    """Test all template-related endpoints."""
    print("🧪 Testing Template API Endpoints")
    print("=" * 50)
    print(f"Testing server at: {BASE_URL}")
    print()
    
    tests_passed = 0
    total_tests = 0
    
    # Test 1: Health check
    print("📋 Testing Basic Endpoints:")
    total_tests += 1
    success, _ = test_endpoint("GET", "/health")
    if success:
        tests_passed += 1
    
    # Test 2: Field definitions
    total_tests += 1
    success, field_defs = test_endpoint("GET", "/field_definitions")
    if success:
        tests_passed += 1
        print(f"   Found {len(field_defs)} field definitions")
    
    # Test 3: List templates
    total_tests += 1
    success, templates_data = test_endpoint("GET", "/list_templates")
    if success:
        tests_passed += 1
        templates = templates_data.get('templates', [])
        print(f"   Found {len(templates)} templates")
        
        # Test 4: Get template details for first template
        if templates:
            total_tests += 1
            first_template = templates[0]['file_id']
            success, template_details = test_endpoint("GET", f"/get_template_details/{first_template}")
            if success:
                tests_passed += 1
                print(f"   Template '{first_template}' has {len(template_details.get('field_mappings', []))} mappings")
    
    print()
    print("📋 Testing Template Application:")
    
    # Test 5: Apply template (this will fail without a real file, but we can test the endpoint)
    total_tests += 1
    apply_data = {
        "template_filename": "Basic.json",
        "file_identifier": "test_file.xlsx",
        "file_type": "XLSX"
    }
    success, _ = test_endpoint("POST", "/apply_template", data=apply_data, expected_status=404)  # Expect 404 since file doesn't exist
    if success:
        tests_passed += 1
        print("   Apply template endpoint responds correctly (404 for missing file)")
    
    print()
    print("📋 Testing Template Creation:")
    
    # Test 6: Save template
    total_tests += 1
    template_data = {
        "template_name": "Test Template",
        "filename": "Test_Template.json",
        "creation_timestamp": "2025-07-30T20:30:00.000Z",
        "field_mappings": [
            {
                "original_header": "Test Header",
                "mapped_field": "InvoiceID"
            }
        ],
        "skip_rows": 5
    }
    success, save_result = test_endpoint("POST", "/save_template", data=template_data)
    if success:
        tests_passed += 1
        print("   Template saved successfully")
        
        # Test 7: Delete the test template
        total_tests += 1
        success, _ = test_endpoint("DELETE", "/delete_template/Test_Template.json")
        if success:
            tests_passed += 1
            print("   Template deleted successfully")
    
    print()
    print("=" * 50)
    print(f"📊 Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All API endpoints are working correctly!")
        print()
        print("✅ Template functionality is fully operational:")
        print("  - Template listing and details retrieval")
        print("  - Template creation and deletion")
        print("  - Template application (endpoint ready)")
        print("  - Field definitions API")
        print()
        print("🌐 Frontend should be accessible at:")
        print(f"  - Main page: {BASE_URL}/")
        print(f"  - Template management: {BASE_URL}/manage_templates")
    else:
        print(f"❌ {total_tests - tests_passed} tests failed. Check the server logs.")
        sys.exit(1)

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Test script to validate Lambda deployment configuration
"""
import os
import sys
import json
from pathlib import Path

def test_lambda_requirements():
    """Test that all Lambda requirements are available"""
    print("🧪 Testing Lambda Requirements")
    print("=" * 40)
    
    required_packages = [
        'flask', 'boto3', 'pandas', 'openpyxl', 
        'pdfplumber', 'requests', 'openai'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package}")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️  Missing packages: {', '.join(missing_packages)}")
        print("Run: pip install -r requirements-lambda.txt")
        return False
    
    print("\n✅ All required packages are available")
    return True

def test_lambda_config():
    """Test Lambda configuration"""
    print("\n🔧 Testing Lambda Configuration")
    print("=" * 40)
    
    # Test environment setup
    os.environ['LAMBDA_ENVIRONMENT'] = 'true'
    
    try:
        from lambda_config import configure_lambda_environment, get_lambda_context
        
        # Test configuration
        configured = configure_lambda_environment()
        print(f"✅ Lambda environment configured: {configured}")
        
        # Test context
        context = get_lambda_context()
        print(f"✅ Lambda context: {context['is_lambda']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Lambda configuration error: {e}")
        return False

def test_app_import():
    """Test that the Flask app can be imported"""
    print("\n📱 Testing Flask App Import")
    print("=" * 40)
    
    try:
        # Set Lambda environment
        os.environ['LAMBDA_ENVIRONMENT'] = 'true'
        
        # Import app
        from app import app
        print("✅ Flask app imported successfully")
        
        # Test basic routes
        with app.test_client() as client:
            response = client.get('/health')
            print(f"✅ Health check: {response.status_code}")
            
            response = client.get('/storage_status')
            print(f"✅ Storage status: {response.status_code}")
        
        return True
        
    except Exception as e:
        print(f"❌ App import error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_sam_template():
    """Test SAM template validity"""
    print("\n📋 Testing SAM Template")
    print("=" * 40)
    
    template_path = Path('template.yaml')
    if not template_path.exists():
        print("❌ template.yaml not found")
        return False
    
    try:
        # Read template as text and check for required sections
        with open(template_path) as f:
            template_content = f.read()
        
        # Check required sections exist in the text
        required_sections = [
            'AWSTemplateFormatVersion',
            'Transform: \'AWS::Serverless-2016-10-31\'',
            'VendorStatementsFunction',
            'VendorStatementsApi',
            'StorageBucket'
        ]
        
        all_found = True
        for section in required_sections:
            if section in template_content:
                print(f"✅ {section}")
            else:
                print(f"❌ Missing {section}")
                all_found = False
        
        # Check for CloudFormation intrinsic functions (normal for SAM)
        if '!Sub' in template_content and '!Ref' in template_content:
            print("✅ CloudFormation intrinsic functions present")
        
        # Check for Lambda handler
        if 'lambda_handler.handler' in template_content:
            print("✅ Lambda handler configured")
        else:
            print("❌ Lambda handler not found")
            all_found = False
        
        return all_found
        
    except Exception as e:
        print(f"❌ SAM template error: {e}")
        return False

def test_deployment_files():
    """Test that all deployment files exist"""
    print("\n📁 Testing Deployment Files")
    print("=" * 40)
    
    required_files = [
        'template.yaml',
        'lambda_handler.py',
        'requirements-lambda.txt',
        'deploy_lambda.sh',
        'lambda_config.py'
    ]
    
    all_exist = True
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path}")
            all_exist = False
    
    return all_exist

def main():
    """Run all tests"""
    print("🚀 Lambda Deployment Configuration Test")
    print("=" * 50)
    
    tests = [
        ("Deployment Files", test_deployment_files),
        ("Lambda Requirements", test_lambda_requirements),
        ("Lambda Configuration", test_lambda_config),
        ("SAM Template", test_sam_template),
        ("Flask App Import", test_app_import),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n📊 Test Summary")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Ready for Lambda deployment.")
        print("\nNext steps:")
        print("1. Run: ./deploy_lambda.sh")
        print("2. Follow the deployment prompts")
        print("3. Test the deployed application")
        return True
    else:
        print(f"\n⚠️  {total - passed} tests failed. Please fix issues before deployment.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
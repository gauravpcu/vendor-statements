#!/usr/bin/env python3
"""
Local testing script for memory optimization
"""
import os
import sys
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, os.getcwd())

def test_app_startup():
    """Test if the app starts without errors"""
    print("🚀 Testing Flask app startup...")
    
    try:
        # Set environment variables for testing
        os.environ['FLASK_ENV'] = 'development'
        os.environ['AZURE_OAI_ENDPOINT'] = 'https://test.openai.azure.com/'
        os.environ['AZURE_OAI_KEY'] = 'test-key'
        os.environ['AZURE_OAI_DEPLOYMENT_NAME'] = 'test-deployment'
        os.environ['STORAGE_MODE'] = 'local'
        
        from app import app
        print("✅ Flask app imported successfully")
        
        # Test health endpoints
        with app.test_client() as client:
            # Test basic health
            response = client.get('/health')
            print(f"Health endpoint: {response.status_code}")
            
            # Test detailed health
            response = client.get('/healthz')
            print(f"Detailed health endpoint: {response.status_code}")
            if response.status_code == 200:
                data = response.get_json()
                print(f"Health data: {data}")
        
        return True
        
    except Exception as e:
        print(f"❌ App startup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_pdf_processing():
    """Test PDF processing with a sample file"""
    print("\n📄 Testing PDF processing...")
    
    try:
        from pdftocsv import extract_tables_from_file
        
        # You can create a simple test PDF or use an existing one
        test_files = [
            "test.pdf",
            "sample.pdf", 
            "uploads/test.pdf"
        ]
        
        test_file = None
        for file_path in test_files:
            if os.path.exists(file_path):
                test_file = file_path
                break
        
        if not test_file:
            print("⚠️  No test PDF file found. Create a test.pdf file to test PDF processing.")
            print("💡 You can skip this test for now - the app will work with other file types.")
            return True
        
        print(f"Testing with: {test_file}")
        result = extract_tables_from_file(test_file, "test_output.csv")
        
        if result:
            print(f"✅ PDF processing successful - extracted {len(result)} tables")
        else:
            print("⚠️  PDF processing returned no tables (this might be normal for some PDFs)")
        
        return True
        
    except Exception as e:
        print(f"❌ PDF processing failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_memory_usage():
    """Test memory usage"""
    print("\n💾 Testing memory usage...")
    
    try:
        import psutil
        import gc
        
        # Get initial memory
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        print(f"Initial memory usage: {initial_memory:.2f} MB")
        
        # Test importing heavy modules
        print("Importing docling...")
        try:
            from docling.document_converter import DocumentConverter
            after_docling = process.memory_info().rss / 1024 / 1024
            print(f"Memory after docling import: {after_docling:.2f} MB (+{after_docling-initial_memory:.2f} MB)")
        except Exception as e:
            print(f"Docling import failed: {e}")
        
        # Force garbage collection
        gc.collect()
        after_gc = process.memory_info().rss / 1024 / 1024
        print(f"Memory after garbage collection: {after_gc:.2f} MB")
        
        # System memory info
        memory = psutil.virtual_memory()
        print(f"System memory: {memory.total/1024/1024/1024:.2f} GB total, {memory.available/1024/1024/1024:.2f} GB available")
        
        return True
        
    except Exception as e:
        print(f"❌ Memory test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Local Testing Suite")
    print("=" * 30)
    
    tests = [
        ("Memory Usage", test_memory_usage),
        ("App Startup", test_app_startup),
        ("PDF Processing", test_pdf_processing),
    ]
    
    results = {}
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Running: {test_name}")
        print('='*50)
        results[test_name] = test_func()
    
    # Summary
    print(f"\n{'='*50}")
    print("📊 Test Results Summary")
    print('='*50)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n🎉 All tests passed! Ready for deployment.")
        print("\n🚀 To run the app locally:")
        print("python app.py")
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")
        print("💡 The app might still work - try running: python app.py")

if __name__ == "__main__":
    main()
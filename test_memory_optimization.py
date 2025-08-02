#!/usr/bin/env python3
"""
Test script to check memory usage and optimize PDF processing
"""
import os
import sys
import psutil
import tracemalloc
from pathlib import Path

def get_memory_usage():
    """Get current memory usage"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024  # MB

def test_pdf_processing():
    """Test PDF processing with memory monitoring"""
    print("🧪 Testing PDF Processing with Memory Monitoring")
    print("=" * 50)
    
    # Start memory tracing
    tracemalloc.start()
    initial_memory = get_memory_usage()
    print(f"Initial memory usage: {initial_memory:.2f} MB")
    
    try:
        # Test with a small PDF first
        from pdftocsv import extract_tables_from_file_pdfplumber
        
        # Create a test file path (you'll need to provide an actual PDF)
        test_pdf = "test_file.pdf"  # Replace with actual test file
        output_csv = "test_output.csv"
        
        if not os.path.exists(test_pdf):
            print(f"❌ Test file {test_pdf} not found")
            print("💡 Please provide a test PDF file to run this test")
            return False
        
        print(f"📄 Processing: {test_pdf}")
        memory_before = get_memory_usage()
        print(f"Memory before processing: {memory_before:.2f} MB")
        
        # Process the file
        result = extract_tables_from_file_pdfplumber(test_pdf, output_csv)
        
        memory_after = get_memory_usage()
        print(f"Memory after processing: {memory_after:.2f} MB")
        print(f"Memory increase: {memory_after - memory_before:.2f} MB")
        
        # Get memory trace
        current, peak = tracemalloc.get_traced_memory()
        print(f"Current memory trace: {current / 1024 / 1024:.2f} MB")
        print(f"Peak memory trace: {peak / 1024 / 1024:.2f} MB")
        
        tracemalloc.stop()
        
        if result:
            print("✅ PDF processing successful")
            return True
        else:
            print("❌ PDF processing failed")
            return False
            
    except Exception as e:
        print(f"❌ Error during PDF processing: {e}")
        traceback.print_exc()
        return False

def test_flask_app():
    """Test Flask app startup"""
    print("\n🌐 Testing Flask App Startup")
    print("=" * 30)
    
    try:
        from app import app
        print("✅ Flask app imported successfully")
        
        # Test health endpoint
        with app.test_client() as client:
            response = client.get('/health')
            if response.status_code == 200:
                print("✅ Health endpoint working")
            else:
                print(f"❌ Health endpoint failed: {response.status_code}")
                
            # Test healthz endpoint
            response = client.get('/healthz')
            if response.status_code == 200:
                print("✅ Detailed health endpoint working")
                print(f"Response: {response.get_json()}")
            else:
                print(f"❌ Detailed health endpoint failed: {response.status_code}")
                
        return True
        
    except Exception as e:
        print(f"❌ Flask app test failed: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Memory Optimization Test Suite")
    print("=" * 40)
    
    # Check system resources
    print(f"💻 System Memory: {psutil.virtual_memory().total / 1024 / 1024 / 1024:.2f} GB")
    print(f"💻 Available Memory: {psutil.virtual_memory().available / 1024 / 1024 / 1024:.2f} GB")
    print(f"💻 CPU Count: {psutil.cpu_count()}")
    
    # Test Flask app
    flask_ok = test_flask_app()
    
    # Test PDF processing
    pdf_ok = test_pdf_processing()
    
    print("\n📊 Test Results Summary")
    print("=" * 25)
    print(f"Flask App: {'✅ PASS' if flask_ok else '❌ FAIL'}")
    print(f"PDF Processing: {'✅ PASS' if pdf_ok else '❌ FAIL'}")
    
    if flask_ok and pdf_ok:
        print("\n🎉 All tests passed! Ready for deployment.")
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")
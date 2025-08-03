#!/usr/bin/env python3
"""
Test PDF processing locally with the HDSupply.pdf file
"""
import os
import sys
import time
import psutil

# Add current directory to Python path
sys.path.insert(0, os.getcwd())

def test_pdf_processing_local():
    """Test PDF processing locally"""
    
    pdf_file = "/Users/gaurav/Desktop/Code/vendor-statements/uploads/HDSupply.pdf"
    
    if not os.path.exists(pdf_file):
        print(f"❌ PDF file not found: {pdf_file}")
        return False
    
    file_size = os.path.getsize(pdf_file) / 1024 / 1024
    print(f"🧪 Testing PDF Processing Locally")
    print(f"📄 File: HDSupply.pdf ({file_size:.2f} MB)")
    print("=" * 50)
    
    # Monitor memory before
    process = psutil.Process()
    initial_memory = process.memory_info().rss / 1024 / 1024
    system_memory = psutil.virtual_memory()
    print(f"💾 Initial memory: Process={initial_memory:.1f}MB, Available={system_memory.available/1024/1024/1024:.1f}GB")
    
    try:
        # Test the main extract function
        from pdftocsv import extract_tables_from_file
        
        print("📤 Processing PDF with extract_tables_from_file...")
        start_time = time.time()
        
        result = extract_tables_from_file(pdf_file, "test_output_local.csv")
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Monitor memory after
        final_memory = process.memory_info().rss / 1024 / 1024
        system_memory_after = psutil.virtual_memory()
        
        print(f"✅ PDF processing completed!")
        print(f"📊 Results:")
        print(f"  - Tables extracted: {len(result) if result else 0}")
        print(f"  - Processing time: {processing_time:.1f} seconds")
        print(f"  - Memory usage: {final_memory - initial_memory:+.1f}MB change")
        print(f"  - System memory: {system_memory_after.available/1024/1024/1024:.1f}GB available")
        
        # Check if output file was created
        if os.path.exists("test_output_local.csv"):
            file_size = os.path.getsize("test_output_local.csv")
            print(f"  - Output file: test_output_local.csv ({file_size} bytes)")
            
            # Show first few lines of output
            with open("test_output_local.csv", 'r') as f:
                lines = f.readlines()[:5]
                print(f"  - Sample output:")
                for i, line in enumerate(lines):
                    print(f"    {i+1}: {line.strip()}")
        
        return True
        
    except Exception as e:
        print(f"❌ PDF processing failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_pdfplumber_directly():
    """Test pdfplumber method directly"""
    
    pdf_file = "/Users/gaurav/Desktop/Code/vendor-statements/uploads/HDSupply.pdf"
    
    print(f"\n🔬 Testing pdfplumber directly")
    print("=" * 35)
    
    try:
        from pdftocsv import extract_tables_from_file_pdfplumber
        
        print("📤 Processing PDF with pdfplumber...")
        start_time = time.time()
        
        result = extract_tables_from_file_pdfplumber(pdf_file, "test_pdfplumber_local.csv")
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        print(f"✅ pdfplumber processing completed!")
        print(f"📊 Results:")
        print(f"  - Tables extracted: {len(result) if result else 0}")
        print(f"  - Processing time: {processing_time:.1f} seconds")
        
        # Show sample data from first table if available
        if result and len(result) > 0:
            first_table = result[0]
            print(f"  - First table shape: {first_table.shape}")
            print(f"  - First table columns: {list(first_table.columns)[:5]}")
            if len(first_table) > 0:
                print(f"  - Sample row: {first_table.iloc[0].to_dict()}")
        
        return True
        
    except Exception as e:
        print(f"❌ pdfplumber processing failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_flask_upload():
    """Test Flask upload endpoint locally"""
    
    print(f"\n🌐 Testing Flask upload endpoint")
    print("=" * 35)
    
    try:
        # Set up environment for testing
        os.environ['FLASK_ENV'] = 'development'
        os.environ['AZURE_OAI_ENDPOINT'] = 'https://procurementiq.openai.azure.com/'
        os.environ['AZURE_OAI_KEY'] = '215ba3947a654a058b4d87ea35e07029'
        os.environ['AZURE_OAI_DEPLOYMENT_NAME'] = 'gpt-4o'
        os.environ['STORAGE_MODE'] = 'local'
        
        from app import app
        
        pdf_file = "/Users/gaurav/Desktop/Code/vendor-statements/uploads/HDSupply.pdf"
        
        with app.test_client() as client:
            print("📤 Uploading PDF via Flask...")
            start_time = time.time()
            
            with open(pdf_file, 'rb') as f:
                response = client.post('/upload', 
                                     data={'files[]': f},
                                     content_type='multipart/form-data')
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            print(f"📊 Flask upload results:")
            print(f"  - Status code: {response.status_code}")
            print(f"  - Processing time: {processing_time:.1f} seconds")
            
            if response.status_code == 200:
                result = response.get_json()
                if isinstance(result, list) and len(result) > 0:
                    upload_result = result[0]
                    print(f"  - Success: {upload_result.get('success')}")
                    print(f"  - File type: {upload_result.get('file_type')}")
                    print(f"  - Headers found: {len(upload_result.get('headers', []))}")
                    print(f"  - Field mappings: {len(upload_result.get('field_mappings', []))}")
                    print(f"  - Message: {upload_result.get('message')}")
                    
                    return True
                else:
                    print(f"  - Unexpected response: {result}")
            else:
                print(f"  - Error response: {response.get_data(as_text=True)}")
            
            return response.status_code == 200
        
    except Exception as e:
        print(f"❌ Flask upload test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 Local PDF Processing Test Suite")
    print("=" * 40)
    
    # System info
    memory = psutil.virtual_memory()
    print(f"💻 System: {memory.total/1024/1024/1024:.1f}GB total, {memory.available/1024/1024/1024:.1f}GB available")
    print(f"💻 CPU cores: {psutil.cpu_count()}")
    
    # Test 1: Direct PDF processing
    test1_success = test_pdf_processing_local()
    
    # Test 2: pdfplumber directly
    test2_success = test_pdfplumber_directly()
    
    # Test 3: Flask upload
    test3_success = test_flask_upload()
    
    # Summary
    print(f"\n📊 Test Results Summary")
    print("=" * 25)
    print(f"Direct PDF processing: {'✅ PASS' if test1_success else '❌ FAIL'}")
    print(f"pdfplumber direct: {'✅ PASS' if test2_success else '❌ FAIL'}")
    print(f"Flask upload: {'✅ PASS' if test3_success else '❌ FAIL'}")
    
    if all([test1_success, test2_success, test3_success]):
        print("\n🎉 All tests passed! Ready for deployment.")
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")
    
    # Cleanup
    for file in ["test_output_local.csv", "test_pdfplumber_local.csv"]:
        if os.path.exists(file):
            os.remove(file)
            print(f"🧹 Cleaned up: {file}")
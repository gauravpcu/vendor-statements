#!/usr/bin/env python3
"""
Test file upload functionality locally
"""

import requests
import json

def test_csv_upload():
    """Test CSV file upload"""
    print("📁 Testing CSV file upload...")
    
    # Create a simple test CSV file
    test_csv_content = """Date,Description,Amount,Vendor
2024-01-01,Office Supplies,100.00,Acme Corp
2024-01-02,Software License,500.00,Tech Solutions
2024-01-03,Consulting Services,1200.00,Business Advisors"""
    
    with open("test_file.csv", "w") as f:
        f.write(test_csv_content)
    
    try:
        # Test file upload
        with open("test_file.csv", "rb") as f:
            files = {"files[]": f}
            response = requests.post("http://localhost:8000/upload", files=files, timeout=60)
        
        if response.status_code == 200:
            print("✅ CSV upload test passed!")
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                print(f"📊 Response: {json.dumps(result[0], indent=2)}")
            else:
                print(f"📊 Response: {result}")
        else:
            print(f"❌ CSV upload test failed: {response.status_code}")
            print(f"Response: {response.text}")
    
    except Exception as e:
        print(f"❌ CSV upload test failed: {e}")
    
    finally:
        # Clean up test file
        import os
        if os.path.exists("test_file.csv"):
            os.remove("test_file.csv")

def test_pdf_upload():
    """Test PDF file upload (if you have a test PDF)"""
    print("\n📄 Testing PDF file upload...")
    
    # You can add a test PDF file here if you have one
    test_pdf_files = ["test.pdf", "sample.pdf", "test_document.pdf"]
    
    for pdf_file in test_pdf_files:
        if os.path.exists(pdf_file):
            print(f"Found test PDF: {pdf_file}")
            try:
                with open(pdf_file, "rb") as f:
                    files = {"files[]": f}
                    response = requests.post("http://localhost:8000/upload", files=files, timeout=120)
                
                if response.status_code == 200:
                    print("✅ PDF upload test passed!")
                    result = response.json()
                    if isinstance(result, list) and len(result) > 0:
                        print(f"📊 Response: {json.dumps(result[0], indent=2)}")
                else:
                    print(f"❌ PDF upload test failed: {response.status_code}")
                    print(f"Response: {response.text}")
                
                return  # Exit after testing first found PDF
                
            except Exception as e:
                print(f"❌ PDF upload test failed: {e}")
    
    print("ℹ️  No test PDF files found. Skipping PDF test.")

if __name__ == "__main__":
    import os
    
    print("🧪 Testing file upload functionality")
    print("=" * 50)
    
    # Test CSV upload
    test_csv_upload()
    
    # Test PDF upload
    test_pdf_upload()
    
    print("\n🎉 Upload tests completed!")
    print("📊 Check Docker logs: docker logs vendor-statements-local-test")
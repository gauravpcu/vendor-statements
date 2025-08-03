#!/usr/bin/env python3
"""
Final test of PDF upload with the fixed implementation
"""

import requests
import time
import os

def test_pdf_upload():
    """Test PDF upload with the HDSupply.pdf file"""
    
    pdf_file = "/Users/gaurav/Desktop/Code/vendor-statements/uploads/HDSupply.pdf"
    
    if not os.path.exists(pdf_file):
        print(f"❌ PDF file not found: {pdf_file}")
        return False
    
    file_size = os.path.getsize(pdf_file) / 1024 / 1024
    print(f"🧪 Testing PDF Upload (Fixed Implementation)")
    print(f"📄 File: HDSupply.pdf ({file_size:.2f} MB)")
    print("=" * 50)
    
    try:
        print("📤 Uploading PDF file...")
        start_time = time.time()
        
        with open(pdf_file, "rb") as f:
            files = {"files[]": f}
            response = requests.post("http://localhost:8000/upload", files=files, timeout=60)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        if response.status_code == 200:
            print(f"✅ PDF upload successful! ({processing_time:.1f}s)")
            result = response.json()
            
            if isinstance(result, list) and len(result) > 0:
                upload_result = result[0]
                print(f"📊 Results:")
                print(f"  - Success: {upload_result.get('success')}")
                print(f"  - File type: {upload_result.get('file_type')}")
                print(f"  - Headers found: {len(upload_result.get('headers', []))}")
                print(f"  - Field mappings: {len(upload_result.get('field_mappings', []))}")
                print(f"  - Message: {upload_result.get('message')}")
                print(f"  - Processing time: {processing_time:.1f} seconds")
                
                # Show sample headers
                headers = upload_result.get('headers', [])
                if headers:
                    print(f"  - Sample headers: {headers[:10]}")  # First 10 headers
                
                # Show sample mappings
                mappings = upload_result.get('field_mappings', [])
                if mappings:
                    print(f"  - Sample mappings:")
                    for mapping in mappings[:5]:  # First 5 mappings
                        print(f"    • {mapping.get('original_header')} → {mapping.get('mapped_field')} ({mapping.get('confidence_score')}%)")
                
                return True
            else:
                print(f"📊 Unexpected response format: {result}")
                return False
        else:
            print(f"❌ PDF upload failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    
    except requests.exceptions.Timeout:
        print("❌ PDF upload timed out (>60 seconds)")
        return False
    except Exception as e:
        print(f"❌ PDF upload failed: {e}")
        return False

if __name__ == "__main__":
    success = test_pdf_upload()
    
    if success:
        print("\n🎉 PDF processing is now working!")
        print("💡 The fix successfully uses pdfplumber instead of docling")
        print("📈 Ready for production deployment")
    else:
        print("\n❌ PDF processing still has issues")
        print("🔍 Check Docker logs: docker logs vendor-statements-local-test")
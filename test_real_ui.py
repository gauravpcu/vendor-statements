#!/usr/bin/env python3
"""
Test the actual web UI by starting Flask server and making real HTTP requests
"""
import subprocess
import time
import requests
import os
import signal
import sys

def start_flask_server():
    """Start Flask server in background"""
    print("🚀 Starting Flask server...")
    
    # Set environment variables
    env = os.environ.copy()
    env.update({
        'FLASK_ENV': 'development',
        'AZURE_OAI_ENDPOINT': 'https://procurementiq.openai.azure.com/',
        'AZURE_OAI_KEY': '215ba3947a654a058b4d87ea35e07029',
        'AZURE_OAI_DEPLOYMENT_NAME': 'gpt-4o',
        'STORAGE_MODE': 'local'
    })
    
    # Start Flask app
    process = subprocess.Popen(['python', 'app.py'], env=env)
    
    # Wait for server to start
    print("⏳ Waiting for server to start...")
    for i in range(10):
        try:
            response = requests.get("http://localhost:8088/healthz", timeout=2)
            if response.status_code == 200:
                print("✅ Server started successfully!")
                return process
        except:
            time.sleep(1)
    
    print("❌ Server failed to start")
    process.terminate()
    return None

def test_real_pdf_upload():
    """Test PDF upload through real web interface"""
    print("\n🧪 Testing Real Web UI PDF Upload")
    print("=" * 40)
    
    pdf_file = "/Users/gaurav/Desktop/Code/vendor-statements/uploads/HDSupply.pdf"
    
    if not os.path.exists(pdf_file):
        print(f"❌ PDF file not found: {pdf_file}")
        return False
    
    file_size = os.path.getsize(pdf_file) / 1024 / 1024
    print(f"📄 File: HDSupply.pdf ({file_size:.2f} MB)")
    
    try:
        print("📤 Uploading PDF via real HTTP request...")
        start_time = time.time()
        
        with open(pdf_file, 'rb') as f:
            files = {'files[]': f}
            # Use longer timeout for PDF processing
            response = requests.post("http://localhost:8088/upload", files=files, timeout=180)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        print(f"📊 Real UI upload results:")
        print(f"  - Status code: {response.status_code}")
        print(f"  - Processing time: {processing_time:.1f} seconds")
        print(f"  - Response size: {len(response.content)} bytes")
        
        if response.status_code == 200:
            try:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    upload_result = result[0]
                    print(f"  - Success: {upload_result.get('success')}")
                    print(f"  - File type: {upload_result.get('file_type')}")
                    print(f"  - Headers found: {len(upload_result.get('headers', []))}")
                    print(f"  - Field mappings: {len(upload_result.get('field_mappings', []))}")
                    print(f"  - Message: {upload_result.get('message')}")
                    return True
                else:
                    print(f"  - Unexpected response format: {result}")
            except Exception as e:
                print(f"  - JSON parse error: {e}")
                print(f"  - Raw response: {response.text[:500]}...")
        else:
            print(f"  - Error response: {response.text[:500]}...")
        
        return response.status_code == 200
        
    except requests.exceptions.Timeout:
        print("❌ Request timed out (>3 minutes)")
        print("💡 This indicates the server is hanging or crashing")
        return False
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False

def main():
    """Main test function"""
    print("🧪 Real Web UI Test Suite")
    print("=" * 30)
    
    # Start Flask server
    server_process = start_flask_server()
    if not server_process:
        print("❌ Failed to start server")
        return
    
    try:
        # Test PDF upload
        success = test_real_pdf_upload()
        
        if success:
            print("\n✅ Real UI test PASSED!")
        else:
            print("\n❌ Real UI test FAILED!")
            print("💡 This explains why the UI doesn't work while test_client() does")
    
    finally:
        # Clean up server
        print("\n🧹 Stopping server...")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_process.kill()
        print("✅ Server stopped")

if __name__ == "__main__":
    main()
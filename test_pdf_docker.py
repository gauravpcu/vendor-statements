#!/usr/bin/env python3
"""
Test PDF processing in Docker with EC2-like constraints
"""

import subprocess
import sys
import time
import requests
import os
import json

def run_command(cmd, check=True):
    """Run a command and return the result"""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False
    if result.stdout:
        print(f"Output: {result.stdout}")
    return True

def test_pdf_upload_docker():
    """Test PDF upload in Docker environment"""
    
    print("🐳 Testing PDF Upload in Docker (EC2-like environment)")
    print("=" * 60)
    
    pdf_file = "/Users/gaurav/Desktop/Code/vendor-statements/uploads/HDSupply.pdf"
    
    # Check if PDF exists
    if not os.path.exists(pdf_file):
        print(f"❌ PDF file not found: {pdf_file}")
        return False
    
    file_size = os.path.getsize(pdf_file) / 1024 / 1024
    print(f"📄 Testing with: {pdf_file}")
    print(f"📊 File size: {file_size:.2f} MB")
    
    # Step 1: Ensure Docker container is running
    print("\n1. Checking Docker container status...")
    result = subprocess.run("docker ps | grep vendor-statements-local-test", shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print("⚠️  Container not running. Starting it...")
        if not run_command("docker start vendor-statements-local-test", check=False):
            print("❌ Failed to start container. Please run ./test_docker_local.sh first")
            return False
        time.sleep(10)
    
    # Step 2: Check container health
    print("\n2. Checking container health...")
    try:
        response = requests.get("http://localhost:8000/healthz", timeout=10)
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ Container healthy: {health_data}")
        else:
            print(f"❌ Container unhealthy: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False
    
    # Step 3: Monitor container resources before upload
    print("\n3. Monitoring container resources...")
    run_command("docker stats vendor-statements-local-test --no-stream")
    
    # Step 4: Test PDF upload
    print("\n4. Testing PDF upload...")
    try:
        print("📤 Uploading PDF file...")
        with open(pdf_file, "rb") as f:
            files = {"files[]": f}
            # Increase timeout for PDF processing
            response = requests.post("http://localhost:8000/upload", files=files, timeout=180)
        
        if response.status_code == 200:
            print("✅ PDF upload successful!")
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                print(f"📊 Response summary:")
                upload_result = result[0]
                print(f"  - Success: {upload_result.get('success')}")
                print(f"  - File type: {upload_result.get('file_type')}")
                print(f"  - Headers found: {len(upload_result.get('headers', []))}")
                print(f"  - Field mappings: {len(upload_result.get('field_mappings', []))}")
                print(f"  - Message: {upload_result.get('message')}")
                
                # Show first few headers and mappings
                if upload_result.get('headers'):
                    print(f"  - Sample headers: {upload_result['headers'][:5]}")
                if upload_result.get('field_mappings'):
                    print(f"  - Sample mappings: {upload_result['field_mappings'][:3]}")
            else:
                print(f"📊 Full response: {result}")
        else:
            print(f"❌ PDF upload failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    
    except requests.exceptions.Timeout:
        print("❌ PDF upload timed out (>3 minutes)")
        print("💡 This suggests memory/processing issues")
        return False
    except Exception as e:
        print(f"❌ PDF upload failed: {e}")
        return False
    
    # Step 5: Check container logs for errors
    print("\n5. Checking container logs for errors...")
    run_command("docker logs vendor-statements-local-test --tail 20")
    
    # Step 6: Monitor container resources after upload
    print("\n6. Monitoring container resources after upload...")
    run_command("docker stats vendor-statements-local-test --no-stream")
    
    return True

def test_pdf_processing_methods():
    """Test different PDF processing methods inside the container"""
    print("\n🔬 Testing PDF Processing Methods Inside Container")
    print("=" * 50)
    
    pdf_file = "/Users/gaurav/Desktop/Code/vendor-statements/uploads/HDSupply.pdf"
    
    # Copy PDF to container
    print("📋 Copying PDF to container...")
    copy_cmd = f"docker cp '{pdf_file}' vendor-statements-local-test:/app/test_hdsupply.pdf"
    if not run_command(copy_cmd):
        return False
    
    # Test pdfplumber method
    print("\n🧪 Testing pdfplumber method...")
    pdfplumber_cmd = """docker exec vendor-statements-local-test python -c "
import sys
sys.path.append('/app')
from pdftocsv import extract_tables_from_file_pdfplumber
import psutil
import gc

print('Memory before:', psutil.virtual_memory().available / 1024 / 1024 / 1024, 'GB')
try:
    result = extract_tables_from_file_pdfplumber('/app/test_hdsupply.pdf', '/app/test_pdfplumber_output.csv')
    print('pdfplumber result:', len(result) if result else 0, 'tables')
    print('Memory after:', psutil.virtual_memory().available / 1024 / 1024 / 1024, 'GB')
except Exception as e:
    print('pdfplumber error:', str(e))
"
"""
    run_command(pdfplumber_cmd, check=False)
    
    # Test docling method (if memory allows)
    print("\n🧪 Testing docling method...")
    docling_cmd = """docker exec vendor-statements-local-test python -c "
import sys
sys.path.append('/app')
from pdftocsv import extract_tables_from_file_docling
import psutil
import gc

available_gb = psutil.virtual_memory().available / 1024 / 1024 / 1024
print('Memory available:', available_gb, 'GB')

if available_gb < 2.0:
    print('Skipping docling - insufficient memory')
else:
    try:
        print('Starting docling processing...')
        result = extract_tables_from_file_docling('/app/test_hdsupply.pdf', '/app/test_docling_output.csv')
        print('docling result:', len(result) if result else 0, 'tables')
        print('Memory after:', psutil.virtual_memory().available / 1024 / 1024 / 1024, 'GB')
    except Exception as e:
        print('docling error:', str(e))
        import traceback
        traceback.print_exc()
"
"""
    run_command(docling_cmd, check=False)
    
    # Test smart fallback method
    print("\n🧪 Testing smart fallback method...")
    smart_cmd = """docker exec vendor-statements-local-test python -c "
import sys
sys.path.append('/app')
from pdftocsv import extract_tables_from_file
import psutil

print('Memory before:', psutil.virtual_memory().available / 1024 / 1024 / 1024, 'GB')
try:
    result = extract_tables_from_file('/app/test_hdsupply.pdf', '/app/test_smart_output.csv')
    print('Smart fallback result:', len(result) if result else 0, 'tables')
    print('Memory after:', psutil.virtual_memory().available / 1024 / 1024 / 1024, 'GB')
except Exception as e:
    print('Smart fallback error:', str(e))
    import traceback
    traceback.print_exc()
"
"""
    run_command(smart_cmd, check=False)

if __name__ == "__main__":
    print("🧪 PDF Docker Testing Suite")
    print("=" * 30)
    
    # Test PDF upload via HTTP
    success = test_pdf_upload_docker()
    
    if success:
        print("\n✅ PDF upload test passed!")
    else:
        print("\n❌ PDF upload test failed!")
        print("🔍 Let's test PDF processing methods directly...")
        test_pdf_processing_methods()
    
    print("\n📊 Test completed!")
    print("💡 Check Docker logs: docker logs vendor-statements-local-test")
    print("💡 Monitor resources: docker stats vendor-statements-local-test")
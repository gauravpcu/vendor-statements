#!/usr/bin/env python3
"""
Test PDF processing memory usage and optimization
"""
import os
import sys
import psutil
import gc
from pathlib import Path

def monitor_memory(label):
    """Monitor memory usage"""
    process = psutil.Process()
    memory_mb = process.memory_info().rss / 1024 / 1024
    system_memory = psutil.virtual_memory()
    available_gb = system_memory.available / 1024 / 1024 / 1024
    print(f"{label}: Process={memory_mb:.1f}MB, Available={available_gb:.1f}GB")
    return memory_mb

def test_pdf_processing_methods():
    """Test different PDF processing methods"""
    print("🧪 Testing PDF Processing Methods")
    print("=" * 40)
    
    # Create a simple test PDF if none exists
    test_files = ["test.pdf", "sample.pdf", "uploads/test.pdf"]
    test_file = None
    
    for file_path in test_files:
        if os.path.exists(file_path):
            test_file = file_path
            break
    
    if not test_file:
        print("⚠️  No test PDF found. Please provide a PDF file to test.")
        print("💡 You can create a simple PDF or use any existing PDF file.")
        return False
    
    print(f"📄 Testing with: {test_file}")
    file_size = os.path.getsize(test_file) / 1024 / 1024
    print(f"📊 File size: {file_size:.2f} MB")
    
    monitor_memory("Initial")
    
    # Test 1: pdfplumber (lightweight)
    print("\n🔬 Test 1: pdfplumber method")
    try:
        from pdftocsv import extract_tables_from_file_pdfplumber
        gc.collect()
        monitor_memory("Before pdfplumber")
        
        result = extract_tables_from_file_pdfplumber(test_file, "test_pdfplumber.csv")
        monitor_memory("After pdfplumber")
        
        if result:
            print(f"✅ pdfplumber: Success - {len(result)} tables extracted")
        else:
            print("⚠️  pdfplumber: No tables found")
        
        gc.collect()
        monitor_memory("After cleanup")
        
    except Exception as e:
        print(f"❌ pdfplumber failed: {e}")
    
    # Test 2: docling (memory-intensive)
    print("\n🔬 Test 2: docling method")
    try:
        from pdftocsv import extract_tables_from_file_docling
        gc.collect()
        monitor_memory("Before docling")
        
        # Check available memory before attempting docling
        available_gb = psutil.virtual_memory().available / 1024 / 1024 / 1024
        if available_gb < 2.0:
            print(f"⚠️  Skipping docling test - insufficient memory ({available_gb:.1f}GB available)")
        else:
            result = extract_tables_from_file_docling(test_file, "test_docling.csv")
            monitor_memory("After docling")
            
            if result:
                print(f"✅ docling: Success - {len(result)} tables extracted")
            else:
                print("⚠️  docling: No tables found")
        
        gc.collect()
        monitor_memory("After cleanup")
        
    except Exception as e:
        print(f"❌ docling failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 3: Smart fallback method
    print("\n🔬 Test 3: Smart fallback method")
    try:
        from pdftocsv import extract_tables_from_file
        gc.collect()
        monitor_memory("Before smart fallback")
        
        result = extract_tables_from_file(test_file, "test_smart.csv")
        monitor_memory("After smart fallback")
        
        if result:
            print(f"✅ Smart fallback: Success - {len(result)} tables extracted")
        else:
            print("⚠️  Smart fallback: No tables found")
        
        gc.collect()
        monitor_memory("After cleanup")
        
    except Exception as e:
        print(f"❌ Smart fallback failed: {e}")
        import traceback
        traceback.print_exc()
    
    return True

def test_memory_limits():
    """Test memory limit enforcement"""
    print("\n💾 Testing Memory Limits")
    print("=" * 25)
    
    try:
        import resource
        
        # Get current limits
        soft, hard = resource.getrlimit(resource.RLIMIT_AS)
        print(f"Current memory limits: soft={soft}, hard={hard}")
        
        # Try to set a reasonable limit (2GB)
        new_limit = 2 * 1024 * 1024 * 1024  # 2GB
        try:
            resource.setrlimit(resource.RLIMIT_AS, (new_limit, hard))
            print(f"✅ Set memory limit to 2GB")
        except:
            print("⚠️  Could not set memory limit (may require privileges)")
        
    except ImportError:
        print("⚠️  Resource module not available (Windows?)")

if __name__ == "__main__":
    print("🧪 PDF Memory Testing Suite")
    print("=" * 30)
    
    # System info
    memory = psutil.virtual_memory()
    print(f"💻 System: {memory.total/1024/1024/1024:.1f}GB total, {memory.available/1024/1024/1024:.1f}GB available")
    print(f"💻 CPU cores: {psutil.cpu_count()}")
    
    # Test memory limits
    test_memory_limits()
    
    # Test PDF processing
    success = test_pdf_processing_methods()
    
    if success:
        print("\n🎉 PDF testing completed!")
        print("\n💡 Recommendations:")
        print("- Use pdfplumber for memory-constrained environments")
        print("- Use docling only when you have >2GB available memory")
        print("- The smart fallback method should handle both cases")
    else:
        print("\n⚠️  PDF testing incomplete - need test PDF file")
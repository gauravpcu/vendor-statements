#!/usr/bin/env python3
"""
Test script to run the application locally with EC2-like Docker configuration
"""

import subprocess
import sys
import time
import requests
import os

def run_command(cmd, check=True):
    """Run a command and return the result"""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False
    print(f"Output: {result.stdout}")
    return True

def test_docker_setup():
    """Test the Docker setup locally"""
    
    print("🐳 Testing Docker setup locally (EC2-like configuration)")
    print("=" * 60)
    
    # Step 1: Build the Docker image
    print("\n1. Building Docker image...")
    if not run_command("docker build -t vendor-statements-local ."):
        return False
    
    # Step 2: Stop any existing container
    print("\n2. Stopping existing container...")
    run_command("docker stop vendor-statements-local-test", check=False)
    run_command("docker rm vendor-statements-local-test", check=False)
    
    # Step 3: Create local directories (like EC2)
    print("\n3. Creating local directories...")
    os.makedirs("./local-test-data/uploads", exist_ok=True)
    os.makedirs("./local-test-data/templates", exist_ok=True)
    os.makedirs("./local-test-data/preferences", exist_ok=True)
    
    # Step 4: Run container with EC2-like settings
    print("\n4. Running container with EC2-like settings...")
    docker_cmd = """docker run -d --name vendor-statements-local-test -p 8000:8000 -v $(pwd)/local-test-data/uploads:/app/uploads -v $(pwd)/local-test-data/templates:/app/templates_storage -v $(pwd)/local-test-data/preferences:/app/learned_preferences_storage --memory="4g" --memory-swap="6g" --cpus="2.0" --env-file .env vendor-statements-local"""
    
    if not run_command(docker_cmd):
        return False
    
    # Step 5: Wait for container to start
    print("\n5. Waiting for container to start...")
    time.sleep(10)
    
    # Step 6: Check container status
    print("\n6. Checking container status...")
    run_command("docker ps | grep vendor-statements-local-test")
    
    # Step 7: Check logs
    print("\n7. Checking container logs...")
    run_command("docker logs vendor-statements-local-test")
    
    return True

if __name__ == "__main__":
    test_docker_setup()
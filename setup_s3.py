#!/usr/bin/env python3
"""
S3 Setup and Configuration Script for Vendor Statements Application
"""
import os
import sys
import boto3
import json
from botocore.exceptions import ClientError, NoCredentialsError
from config.s3_config import S3Config

def check_aws_credentials():
    """Check if AWS credentials are configured"""
    print("🔍 Checking AWS credentials...")
    
    try:
        # Try to create a session
        session = boto3.Session()
        credentials = session.get_credentials()
        
        if credentials is None:
            print("❌ No AWS credentials found.")
            print("   Please configure credentials using one of these methods:")
            print("   1. Set environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY")
            print("   2. Configure AWS CLI: aws configure")
            print("   3. Use IAM roles (for EC2/Lambda)")
            return False
        
        print(f"✅ AWS credentials found (Access Key: {credentials.access_key[:8]}...)")
        return True
        
    except Exception as e:
        print(f"❌ Error checking credentials: {e}")
        return False

def test_s3_connection():
    """Test S3 connection and permissions"""
    print("\n🔗 Testing S3 connection...")
    
    try:
        s3_client = boto3.client('s3', region_name=S3Config.REGION)
        
        # List buckets to test connection
        response = s3_client.list_buckets()
        print(f"✅ Successfully connected to S3 (found {len(response['Buckets'])} buckets)")
        
        return s3_client
        
    except NoCredentialsError:
        print("❌ AWS credentials not configured")
        return None
    except ClientError as e:
        print(f"❌ S3 connection failed: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None

def check_bucket_exists(s3_client, bucket_name):
    """Check if the specified bucket exists and is accessible"""
    print(f"\n🪣 Checking bucket: {bucket_name}")
    
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        print(f"✅ Bucket '{bucket_name}' exists and is accessible")
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            print(f"❌ Bucket '{bucket_name}' does not exist")
        elif error_code == '403':
            print(f"❌ Access denied to bucket '{bucket_name}'")
        else:
            print(f"❌ Error accessing bucket '{bucket_name}': {e}")
        return False

def create_bucket(s3_client, bucket_name, region):
    """Create a new S3 bucket"""
    print(f"\n🏗️  Creating bucket: {bucket_name}")
    
    try:
        if region == 'us-east-1':
            # us-east-1 doesn't need LocationConstraint
            s3_client.create_bucket(Bucket=bucket_name)
        else:
            s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': region}
            )
        
        print(f"✅ Successfully created bucket '{bucket_name}'")
        return True
        
    except ClientError as e:
        print(f"❌ Failed to create bucket: {e}")
        return False

def setup_bucket_structure(s3_client, bucket_name):
    """Create the folder structure in the S3 bucket"""
    print(f"\n📁 Setting up folder structure in bucket: {bucket_name}")
    
    folders = [
        S3Config.TEMPLATES_PREFIX,
        S3Config.UPLOADS_PREFIX,
        S3Config.PROCESSED_PREFIX,
        S3Config.CACHE_PREFIX
    ]
    
    for folder in folders:
        try:
            # Create a placeholder object to represent the folder
            s3_client.put_object(
                Bucket=bucket_name,
                Key=f"{folder}.gitkeep",
                Body=b"# This file maintains the folder structure\n"
            )
            print(f"✅ Created folder: {folder}")
            
        except ClientError as e:
            print(f"❌ Failed to create folder {folder}: {e}")
            return False
    
    return True

def test_bucket_operations(s3_client, bucket_name):
    """Test basic bucket operations"""
    print(f"\n🧪 Testing bucket operations...")
    
    test_key = "test/setup-test.txt"
    test_content = "This is a test file created during S3 setup."
    
    try:
        # Test upload
        s3_client.put_object(
            Bucket=bucket_name,
            Key=test_key,
            Body=test_content.encode('utf-8'),
            ContentType='text/plain'
        )
        print("✅ Upload test successful")
        
        # Test download
        response = s3_client.get_object(Bucket=bucket_name, Key=test_key)
        downloaded_content = response['Body'].read().decode('utf-8')
        
        if downloaded_content == test_content:
            print("✅ Download test successful")
        else:
            print("❌ Download test failed - content mismatch")
            return False
        
        # Test delete
        s3_client.delete_object(Bucket=bucket_name, Key=test_key)
        print("✅ Delete test successful")
        
        return True
        
    except ClientError as e:
        print(f"❌ Bucket operations test failed: {e}")
        return False

def generate_env_config():
    """Generate .env configuration based on current settings"""
    print("\n📝 Generating .env configuration...")
    
    config_lines = [
        "# AWS S3 Configuration - Generated by setup_s3.py",
        f"AWS_S3_BUCKET_NAME={S3Config.BUCKET_NAME or 'your-vendor-statements-bucket'}",
        f"AWS_REGION={S3Config.REGION}",
        "",
        "# Set these with your actual AWS credentials",
        f"AWS_ACCESS_KEY_ID={S3Config.ACCESS_KEY_ID or 'your-access-key-id'}",
        f"AWS_SECRET_ACCESS_KEY={S3Config.SECRET_ACCESS_KEY or 'your-secret-access-key'}",
        "",
        "# Storage Configuration",
        "STORAGE_MODE=s3  # Enable S3 storage",
        "",
        "# S3 Prefixes",
        f"S3_TEMPLATES_PREFIX={S3Config.TEMPLATES_PREFIX}",
        f"S3_UPLOADS_PREFIX={S3Config.UPLOADS_PREFIX}",
        f"S3_PROCESSED_PREFIX={S3Config.PROCESSED_PREFIX}",
        f"S3_CACHE_PREFIX={S3Config.CACHE_PREFIX}",
        "",
        "# File Settings",
        f"MAX_FILE_SIZE={S3Config.MAX_FILE_SIZE // (1024*1024)}  # MB",
        f"PRESIGNED_URL_EXPIRATION={S3Config.PRESIGNED_URL_EXPIRATION}  # seconds",
    ]
    
    env_content = "\n".join(config_lines)
    
    # Write to .env.s3 file
    with open('.env.s3', 'w') as f:
        f.write(env_content)
    
    print("✅ Configuration saved to .env.s3")
    print("   Copy the contents to your .env file to enable S3 storage")

def main():
    """Main setup function"""
    print("🚀 Vendor Statements S3 Setup")
    print("=" * 50)
    
    # Check configuration
    config_validation = S3Config.validate_config()
    print(f"📋 Current configuration:")
    print(f"   Storage Mode: {S3Config.STORAGE_MODE}")
    print(f"   Bucket Name: {S3Config.BUCKET_NAME or 'Not configured'}")
    print(f"   Region: {S3Config.REGION}")
    
    if config_validation['issues']:
        print("\n⚠️  Configuration Issues:")
        for issue in config_validation['issues']:
            print(f"   - {issue}")
    
    if config_validation['warnings']:
        print("\n⚠️  Configuration Warnings:")
        for warning in config_validation['warnings']:
            print(f"   - {warning}")
    
    # Check AWS credentials
    if not check_aws_credentials():
        print("\n❌ Setup cannot continue without AWS credentials")
        return False
    
    # Test S3 connection
    s3_client = test_s3_connection()
    if not s3_client:
        print("\n❌ Setup cannot continue without S3 connection")
        return False
    
    # Get bucket name
    bucket_name = S3Config.BUCKET_NAME
    if not bucket_name:
        bucket_name = input("\n📝 Enter S3 bucket name: ").strip()
        if not bucket_name:
            print("❌ Bucket name is required")
            return False
    
    # Check if bucket exists
    if not check_bucket_exists(s3_client, bucket_name):
        create_new = input(f"\n❓ Create bucket '{bucket_name}'? (y/N): ").strip().lower()
        if create_new == 'y':
            if not create_bucket(s3_client, bucket_name, S3Config.REGION):
                return False
        else:
            print("❌ Setup cannot continue without a valid bucket")
            return False
    
    # Setup bucket structure
    if not setup_bucket_structure(s3_client, bucket_name):
        print("⚠️  Failed to setup complete folder structure")
    
    # Test bucket operations
    if not test_bucket_operations(s3_client, bucket_name):
        print("⚠️  Bucket operations test failed")
    
    # Generate configuration
    generate_env_config()
    
    print("\n🎉 S3 Setup Complete!")
    print("=" * 50)
    print("Next steps:")
    print("1. Copy .env.s3 contents to your .env file")
    print("2. Set STORAGE_MODE=s3 in your .env file")
    print("3. Restart your application")
    print("4. Check /storage_status endpoint to verify configuration")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error during setup: {e}")
        sys.exit(1)
#!/usr/bin/env python3
"""
Interactive S3 Configuration Script
This script helps you configure AWS S3 settings for the Vendor Statements application.
"""
import os
import re
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

def get_user_input(prompt, default=None, required=True):
    """Get user input with optional default value"""
    if default:
        full_prompt = f"{prompt} [{default}]: "
    else:
        full_prompt = f"{prompt}: "
    
    while True:
        value = input(full_prompt).strip()
        if value:
            return value
        elif default:
            return default
        elif not required:
            return ""
        else:
            print("This field is required. Please enter a value.")

def validate_bucket_name(bucket_name):
    """Validate S3 bucket name according to AWS rules"""
    if not bucket_name:
        return False, "Bucket name cannot be empty"
    
    if len(bucket_name) < 3 or len(bucket_name) > 63:
        return False, "Bucket name must be between 3 and 63 characters"
    
    if not re.match(r'^[a-z0-9][a-z0-9.-]*[a-z0-9]$', bucket_name):
        return False, "Bucket name must start and end with a letter or number, and contain only lowercase letters, numbers, hyphens, and periods"
    
    if '..' in bucket_name or '.-' in bucket_name or '-.' in bucket_name:
        return False, "Bucket name cannot contain consecutive periods or hyphens adjacent to periods"
    
    # Check if it looks like an IP address
    if re.match(r'^\d+\.\d+\.\d+\.\d+$', bucket_name):
        return False, "Bucket name cannot be formatted as an IP address"
    
    return True, "Valid bucket name"

def test_aws_credentials(access_key, secret_key, region):
    """Test AWS credentials by trying to list buckets"""
    try:
        client = boto3.client(
            's3',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
        
        # Try to list buckets
        response = client.list_buckets()
        return True, f"✅ Credentials valid. Found {len(response['Buckets'])} buckets."
        
    except NoCredentialsError:
        return False, "❌ Invalid credentials"
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'InvalidAccessKeyId':
            return False, "❌ Invalid Access Key ID"
        elif error_code == 'SignatureDoesNotMatch':
            return False, "❌ Invalid Secret Access Key"
        else:
            return False, f"❌ AWS Error: {e.response['Error']['Message']}"
    except Exception as e:
        return False, f"❌ Unexpected error: {str(e)}"

def check_bucket_exists(client, bucket_name):
    """Check if bucket exists and is accessible"""
    try:
        client.head_bucket(Bucket=bucket_name)
        return True, "✅ Bucket exists and is accessible"
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            return False, "❌ Bucket does not exist"
        elif error_code == '403':
            return False, "❌ Access denied to bucket"
        else:
            return False, f"❌ Error: {e.response['Error']['Message']}"

def create_bucket(client, bucket_name, region):
    """Create a new S3 bucket"""
    try:
        if region == 'us-east-1':
            client.create_bucket(Bucket=bucket_name)
        else:
            client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': region}
            )
        return True, f"✅ Successfully created bucket '{bucket_name}'"
    except ClientError as e:
        return False, f"❌ Failed to create bucket: {e.response['Error']['Message']}"

def update_env_file(config):
    """Update the .env file with new S3 configuration"""
    env_path = '.env'
    
    # Read current .env file
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            content = f.read()
    else:
        content = ""
    
    # Update S3 configuration
    s3_config = f"""
# ===== AWS S3 Configuration (Updated by configure_s3.py) =====
AWS_S3_BUCKET_NAME={config['bucket_name']}
AWS_REGION={config['region']}
AWS_ACCESS_KEY_ID={config['access_key']}
AWS_SECRET_ACCESS_KEY={config['secret_key']}

# Storage Configuration
STORAGE_MODE={config['storage_mode']}

# S3 Prefixes for organizing files
S3_TEMPLATES_PREFIX={config['templates_prefix']}
S3_UPLOADS_PREFIX={config['uploads_prefix']}
S3_PROCESSED_PREFIX={config['processed_prefix']}
S3_CACHE_PREFIX={config['cache_prefix']}

# File Settings
MAX_FILE_SIZE={config['max_file_size']}
PRESIGNED_URL_EXPIRATION={config['presigned_url_expiration']}

# Local Fallback Directories
LOCAL_TEMPLATES_DIR={config['local_templates_dir']}
LOCAL_UPLOADS_DIR={config['local_uploads_dir']}
"""
    
    # Remove existing S3 configuration
    lines = content.split('\n')
    new_lines = []
    skip_section = False
    
    for line in lines:
        if line.strip().startswith('# ===== AWS S3 Configuration'):
            skip_section = True
            continue
        elif line.strip().startswith('# =====') and skip_section:
            skip_section = False
            new_lines.append(line)
        elif not skip_section and not any(line.startswith(key) for key in [
            'AWS_S3_BUCKET_NAME', 'AWS_REGION', 'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY',
            'STORAGE_MODE', 'S3_TEMPLATES_PREFIX', 'S3_UPLOADS_PREFIX', 'S3_PROCESSED_PREFIX',
            'S3_CACHE_PREFIX', 'MAX_FILE_SIZE', 'PRESIGNED_URL_EXPIRATION',
            'LOCAL_TEMPLATES_DIR', 'LOCAL_UPLOADS_DIR'
        ]):
            new_lines.append(line)
    
    # Add new S3 configuration
    new_content = '\n'.join(new_lines) + s3_config
    
    # Write updated .env file
    with open(env_path, 'w') as f:
        f.write(new_content)
    
    print(f"✅ Updated {env_path} with new S3 configuration")

def main():
    """Main configuration function"""
    print("🚀 AWS S3 Configuration for Vendor Statements Application")
    print("=" * 60)
    print()
    
    # Get AWS credentials
    print("📋 AWS Credentials Configuration")
    print("-" * 30)
    
    access_key = get_user_input("AWS Access Key ID")
    secret_key = get_user_input("AWS Secret Access Key")
    region = get_user_input("AWS Region", default="us-east-1")
    
    # Test credentials
    print("\n🔍 Testing AWS credentials...")
    valid, message = test_aws_credentials(access_key, secret_key, region)
    print(message)
    
    if not valid:
        print("\n❌ Cannot continue with invalid credentials.")
        return False
    
    # Get bucket configuration
    print("\n🪣 S3 Bucket Configuration")
    print("-" * 30)
    
    while True:
        bucket_name = get_user_input("S3 Bucket Name", default="vendor-statements-app")
        valid, message = validate_bucket_name(bucket_name)
        print(message)
        if valid:
            break
    
    # Check if bucket exists
    client = boto3.client(
        's3',
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region
    )
    
    exists, message = check_bucket_exists(client, bucket_name)
    print(message)
    
    if not exists:
        create_bucket_choice = get_user_input(
            f"Create bucket '{bucket_name}'? (y/n)", 
            default="y"
        ).lower()
        
        if create_bucket_choice == 'y':
            success, message = create_bucket(client, bucket_name, region)
            print(message)
            if not success:
                return False
        else:
            print("❌ Cannot continue without a valid bucket.")
            return False
    
    # Get storage configuration
    print("\n⚙️  Storage Configuration")
    print("-" * 30)
    
    storage_mode = get_user_input("Storage Mode (local/s3)", default="s3")
    templates_prefix = get_user_input("Templates Prefix", default="templates/")
    uploads_prefix = get_user_input("Uploads Prefix", default="uploads/")
    processed_prefix = get_user_input("Processed Files Prefix", default="processed/")
    cache_prefix = get_user_input("Cache Prefix", default="cache/")
    
    max_file_size = get_user_input("Max File Size (MB)", default="50")
    presigned_url_expiration = get_user_input("Presigned URL Expiration (seconds)", default="3600")
    
    local_templates_dir = get_user_input("Local Templates Directory", default="templates")
    local_uploads_dir = get_user_input("Local Uploads Directory", default="uploads")
    
    # Create configuration
    config = {
        'bucket_name': bucket_name,
        'region': region,
        'access_key': access_key,
        'secret_key': secret_key,
        'storage_mode': storage_mode,
        'templates_prefix': templates_prefix,
        'uploads_prefix': uploads_prefix,
        'processed_prefix': processed_prefix,
        'cache_prefix': cache_prefix,
        'max_file_size': max_file_size,
        'presigned_url_expiration': presigned_url_expiration,
        'local_templates_dir': local_templates_dir,
        'local_uploads_dir': local_uploads_dir
    }
    
    # Show configuration summary
    print("\n📋 Configuration Summary")
    print("-" * 30)
    print(f"Bucket Name: {bucket_name}")
    print(f"Region: {region}")
    print(f"Storage Mode: {storage_mode}")
    print(f"Templates Prefix: {templates_prefix}")
    print(f"Uploads Prefix: {uploads_prefix}")
    
    # Confirm and save
    confirm = get_user_input("\nSave this configuration to .env file? (y/n)", default="y").lower()
    
    if confirm == 'y':
        update_env_file(config)
        
        print("\n🎉 S3 Configuration Complete!")
        print("=" * 60)
        print("Next steps:")
        print("1. Restart your application")
        print("2. Check /storage_status endpoint to verify configuration")
        print("3. Test template and file operations")
        print("\nTo test the configuration, run:")
        print("  python setup_s3.py")
        
        return True
    else:
        print("❌ Configuration cancelled.")
        return False

if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n❌ Configuration cancelled by user")
        exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        exit(1)
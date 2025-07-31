"""
Lambda-specific configuration for Vendor Statements application
"""
import os
import tempfile
import logging

def configure_lambda_environment():
    """Configure the application for Lambda environment"""
    
    # Set up temporary directories for Lambda
    if os.environ.get('LAMBDA_ENVIRONMENT'):
        # Use Lambda's writable /tmp directory
        temp_dir = '/tmp'
        
        # Create necessary directories
        upload_dir = os.path.join(temp_dir, 'uploads')
        templates_dir = os.path.join(temp_dir, 'templates_storage')
        preferences_dir = os.path.join(temp_dir, 'learned_preferences_storage')
        
        os.makedirs(upload_dir, exist_ok=True)
        os.makedirs(templates_dir, exist_ok=True)
        os.makedirs(preferences_dir, exist_ok=True)
        
        # Override default directories
        os.environ['UPLOAD_FOLDER'] = upload_dir
        os.environ['TEMPLATES_DIR'] = templates_dir
        os.environ['LEARNED_PREFERENCES_DIR'] = preferences_dir
        
        # Configure logging for Lambda
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Disable some verbose logging in Lambda
        logging.getLogger('boto3').setLevel(logging.WARNING)
        logging.getLogger('botocore').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        
        print(f"Lambda environment configured:")
        print(f"  Upload dir: {upload_dir}")
        print(f"  Templates dir: {templates_dir}")
        print(f"  Preferences dir: {preferences_dir}")
        
        return True
    
    return False

def get_lambda_context():
    """Get Lambda-specific context information"""
    return {
        'is_lambda': os.environ.get('LAMBDA_ENVIRONMENT', 'false').lower() == 'true',
        'aws_region': os.environ.get('AWS_REGION', 'us-east-1'),
        'function_name': os.environ.get('AWS_LAMBDA_FUNCTION_NAME', 'unknown'),
        'function_version': os.environ.get('AWS_LAMBDA_FUNCTION_VERSION', 'unknown'),
        'memory_limit': os.environ.get('AWS_LAMBDA_FUNCTION_MEMORY_SIZE', 'unknown'),
        'remaining_time': None  # Will be set by handler if available
    }

def optimize_for_lambda():
    """Apply Lambda-specific optimizations"""
    
    if not os.environ.get('LAMBDA_ENVIRONMENT'):
        return
    
    # Reduce memory usage
    import gc
    gc.collect()
    
    # Set smaller limits for Lambda
    os.environ.setdefault('MAX_UPLOAD_FILES', '5')  # Reduced from 10
    os.environ.setdefault('MAX_FILE_SIZE', '25')    # Reduced from 50MB
    os.environ.setdefault('PROCESSING_TIMEOUT', '240')  # 4 minutes max
    
    # Configure for S3 storage (required in Lambda)
    if not os.environ.get('STORAGE_MODE'):
        os.environ['STORAGE_MODE'] = 's3'
    
    print("Lambda optimizations applied:")
    print(f"  Max upload files: {os.environ.get('MAX_UPLOAD_FILES')}")
    print(f"  Max file size: {os.environ.get('MAX_FILE_SIZE')}MB")
    print(f"  Processing timeout: {os.environ.get('PROCESSING_TIMEOUT')}s")
    print(f"  Storage mode: {os.environ.get('STORAGE_MODE')}")

# Auto-configure when imported
if __name__ != '__main__':
    configure_lambda_environment()
    optimize_for_lambda()
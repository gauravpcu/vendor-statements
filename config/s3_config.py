"""
S3 Configuration Settings
"""
import os
from typing import Dict, Any

class S3Config:
    """S3 configuration class"""
    
    # S3 Bucket Configuration
    BUCKET_NAME = os.getenv('AWS_S3_BUCKET_NAME')
    REGION = os.getenv('AWS_REGION', 'us-east-1')
    
    # AWS Credentials (can also be configured via IAM roles)
    ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    
    # S3 Prefixes for organizing files
    TEMPLATES_PREFIX = os.getenv('S3_TEMPLATES_PREFIX', 'templates/')
    UPLOADS_PREFIX = os.getenv('S3_UPLOADS_PREFIX', 'uploads/')
    PROCESSED_PREFIX = os.getenv('S3_PROCESSED_PREFIX', 'processed/')
    CACHE_PREFIX = os.getenv('S3_CACHE_PREFIX', 'cache/')
    
    # File Storage Settings
    MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', '50')) * 1024 * 1024  # 50MB default
    ALLOWED_EXTENSIONS = {
        'templates': ['.json'],
        'uploads': ['.pdf', '.csv', '.xlsx', '.xls'],
        'processed': ['.csv', '.json']
    }
    
    # Presigned URL Settings
    PRESIGNED_URL_EXPIRATION = int(os.getenv('PRESIGNED_URL_EXPIRATION', '3600'))  # 1 hour
    
    # Storage Mode Configuration
    STORAGE_MODE = os.getenv('STORAGE_MODE', 'local')  # 'local' or 's3'
    
    # Local fallback directories (when S3 is not available)
    LOCAL_TEMPLATES_DIR = os.getenv('LOCAL_TEMPLATES_DIR', 'templates_storage')
    LOCAL_UPLOADS_DIR = os.getenv('LOCAL_UPLOADS_DIR', 'uploads')
    
    @classmethod
    def is_s3_enabled(cls) -> bool:
        """Check if S3 is properly configured"""
        return (
            cls.STORAGE_MODE == 's3' and
            cls.BUCKET_NAME is not None and
            (cls.ACCESS_KEY_ID is not None or os.getenv('AWS_EXECUTION_ENV') is not None)  # IAM role or explicit credentials
        )
    
    @classmethod
    def get_storage_config(cls) -> Dict[str, Any]:
        """Get current storage configuration"""
        return {
            'storage_mode': cls.STORAGE_MODE,
            's3_enabled': cls.is_s3_enabled(),
            'bucket_name': cls.BUCKET_NAME,
            'region': cls.REGION,
            'templates_prefix': cls.TEMPLATES_PREFIX,
            'uploads_prefix': cls.UPLOADS_PREFIX,
            'max_file_size': cls.MAX_FILE_SIZE,
            'presigned_url_expiration': cls.PRESIGNED_URL_EXPIRATION
        }
    
    @classmethod
    def validate_config(cls) -> Dict[str, Any]:
        """Validate S3 configuration and return status"""
        issues = []
        warnings = []
        
        if cls.STORAGE_MODE == 's3':
            if not cls.BUCKET_NAME:
                issues.append("AWS_S3_BUCKET_NAME is required when STORAGE_MODE=s3")
            
            if not cls.ACCESS_KEY_ID and not os.getenv('AWS_EXECUTION_ENV'):
                warnings.append("AWS_ACCESS_KEY_ID not set. Ensure IAM role is configured for AWS access.")
            
            if not cls.SECRET_ACCESS_KEY and not os.getenv('AWS_EXECUTION_ENV'):
                warnings.append("AWS_SECRET_ACCESS_KEY not set. Ensure IAM role is configured for AWS access.")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'config': cls.get_storage_config()
        }

# Environment variables template for .env file
ENV_TEMPLATE = """
# AWS S3 Configuration
AWS_S3_BUCKET_NAME=your-vendor-statements-bucket
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key-id
AWS_SECRET_ACCESS_KEY=your-secret-access-key

# Storage Configuration
STORAGE_MODE=s3  # 'local' or 's3'

# S3 Prefixes (optional - defaults provided)
S3_TEMPLATES_PREFIX=templates/
S3_UPLOADS_PREFIX=uploads/
S3_PROCESSED_PREFIX=processed/
S3_CACHE_PREFIX=cache/

# File Settings
MAX_FILE_SIZE=50  # MB
PRESIGNED_URL_EXPIRATION=3600  # seconds

# Local Fallback Directories
LOCAL_TEMPLATES_DIR=templates
LOCAL_UPLOADS_DIR=uploads
"""
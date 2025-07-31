# S3 Integration for Vendor Statements Application

This document explains how to configure and use AWS S3 storage for templates and files in the Vendor Statements application.

## Overview

The application now supports hybrid storage with both local filesystem and AWS S3 options:

- **Local Storage**: Files and templates stored on local filesystem (default)
- **S3 Storage**: Files and templates stored in AWS S3 bucket
- **Hybrid Mode**: Local processing with S3 backup/sync

## Features

### Template Management
- ✅ Store templates in S3 with organized folder structure
- ✅ List, create, update, and delete templates from S3
- ✅ Automatic conflict detection and resolution
- ✅ Fallback to local storage if S3 is unavailable

### File Management
- ✅ Upload files to S3 with automatic organization
- ✅ Generate presigned URLs for secure file access
- ✅ Automatic file type detection and metadata
- ✅ Backup uploaded files to S3 while processing locally

### Storage Service
- ✅ Unified API for both local and S3 storage
- ✅ Automatic failover and error handling
- ✅ Configuration validation and health checks
- ✅ Storage status monitoring endpoint

## Configuration

### Environment Variables

Create a `.env` file with the following S3 configuration:

```bash
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
```

### AWS Credentials

You can configure AWS credentials in several ways:

1. **Environment Variables** (recommended for development):
   ```bash
   AWS_ACCESS_KEY_ID=your-access-key-id
   AWS_SECRET_ACCESS_KEY=your-secret-access-key
   ```

2. **AWS CLI Configuration**:
   ```bash
   aws configure
   ```

3. **IAM Roles** (recommended for production):
   - EC2 instance roles
   - Lambda execution roles
   - ECS task roles

## Setup

### Automated Setup

Use the provided setup script to configure S3:

```bash
python setup_s3.py
```

This script will:
- ✅ Check AWS credentials
- ✅ Test S3 connection
- ✅ Create bucket if needed
- ✅ Setup folder structure
- ✅ Test bucket operations
- ✅ Generate configuration

### Manual Setup

1. **Create S3 Bucket**:
   ```bash
   aws s3 mb s3://your-vendor-statements-bucket --region us-east-1
   ```

2. **Create Folder Structure**:
   ```bash
   aws s3api put-object --bucket your-vendor-statements-bucket --key templates/.gitkeep
   aws s3api put-object --bucket your-vendor-statements-bucket --key uploads/.gitkeep
   aws s3api put-object --bucket your-vendor-statements-bucket --key processed/.gitkeep
   aws s3api put-object --bucket your-vendor-statements-bucket --key cache/.gitkeep
   ```

3. **Set Bucket Policy** (optional):
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Principal": {
           "AWS": "arn:aws:iam::YOUR-ACCOUNT-ID:user/YOUR-USER"
         },
         "Action": [
           "s3:GetObject",
           "s3:PutObject",
           "s3:DeleteObject",
           "s3:ListBucket"
         ],
         "Resource": [
           "arn:aws:s3:::your-vendor-statements-bucket",
           "arn:aws:s3:::your-vendor-statements-bucket/*"
         ]
       }
     ]
   }
   ```

## Usage

### Storage Status

Check storage configuration and health:

```bash
curl http://localhost:5000/storage_status
```

Response:
```json
{
  "storage_info": {
    "backend": "s3",
    "config": {
      "storage_mode": "s3",
      "s3_enabled": true,
      "bucket_name": "your-vendor-statements-bucket",
      "region": "us-east-1"
    },
    "s3_available": true
  },
  "config_validation": {
    "valid": true,
    "issues": [],
    "warnings": []
  },
  "templates_count": 5,
  "status": "healthy"
}
```

### Template Operations

All existing template operations work transparently with S3:

- **List Templates**: `GET /list_templates`
- **Get Template**: `GET /get_template_details/<template_name>`
- **Save Template**: `POST /save_template`
- **Delete Template**: `DELETE /delete_template/<template_name>`

### File Operations

File uploads automatically save to both local and S3 (if enabled):

```python
# Upload response includes S3 information
{
  "filename": "statement.pdf",
  "success": true,
  "s3_key": "uploads/statement.pdf",
  "storage_backend": "s3"
}
```

## Architecture

### Storage Service Layer

```
┌─────────────────┐
│   Application   │
└─────────┬───────┘
          │
┌─────────▼───────┐
│ Storage Service │  ← Unified API
└─────────┬───────┘
          │
    ┌─────▼─────┐
    │           │
┌───▼───┐   ┌───▼───┐
│ Local │   │  S3   │
│Storage│   │Service│
└───────┘   └───────┘
```

### File Organization

```
S3 Bucket Structure:
├── templates/
│   ├── vendor1.json
│   ├── vendor2.json
│   └── ...
├── uploads/
│   ├── 2024/01/15/
│   │   ├── statement1.pdf
│   │   └── statement2.xlsx
│   └── ...
├── processed/
│   ├── extracted_data.csv
│   └── ...
└── cache/
    ├── extracted_text/
    └── ...
```

## Error Handling

The storage service includes comprehensive error handling:

- **Connection Failures**: Automatic fallback to local storage
- **Permission Errors**: Clear error messages and suggestions
- **Bucket Not Found**: Automatic bucket creation (if permissions allow)
- **Network Issues**: Retry logic with exponential backoff

## Monitoring

### Health Checks

- **Storage Status Endpoint**: `/storage_status`
- **Template Count Monitoring**: Track template operations
- **File Upload Metrics**: Monitor S3 upload success/failure rates

### Logging

All storage operations are logged with appropriate levels:

```python
logger.info("Successfully uploaded template 'vendor1' to S3")
logger.warning("S3 service not enabled. Cannot upload template.")
logger.error("Error uploading template 'vendor1' to S3: Access Denied")
```

## Security

### Best Practices

1. **Use IAM Roles** in production instead of access keys
2. **Enable S3 Bucket Versioning** for data protection
3. **Configure Bucket Encryption** at rest
4. **Use VPC Endpoints** for private S3 access
5. **Implement Bucket Policies** for access control

### Permissions Required

Minimum IAM permissions needed:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket",
        "s3:GetBucketLocation"
      ],
      "Resource": [
        "arn:aws:s3:::your-vendor-statements-bucket",
        "arn:aws:s3:::your-vendor-statements-bucket/*"
      ]
    }
  ]
}
```

## Troubleshooting

### Common Issues

1. **"AWS credentials not found"**
   - Solution: Configure AWS credentials using one of the methods above

2. **"Bucket does not exist"**
   - Solution: Create bucket or run `python setup_s3.py`

3. **"Access denied to S3 bucket"**
   - Solution: Check IAM permissions and bucket policies

4. **"Storage service not enabled"**
   - Solution: Set `STORAGE_MODE=s3` in your `.env` file

### Debug Mode

Enable debug logging for storage operations:

```python
import logging
logging.getLogger('storage_service').setLevel(logging.DEBUG)
logging.getLogger('s3_service').setLevel(logging.DEBUG)
```

## Migration

### From Local to S3

To migrate existing templates and files to S3:

1. **Set up S3 configuration** (keep `STORAGE_MODE=local` initially)
2. **Run migration script**:
   ```bash
   python migrate_to_s3.py
   ```
3. **Verify migration** using storage status endpoint
4. **Switch to S3**: Set `STORAGE_MODE=s3`
5. **Test functionality** with existing templates

### From S3 to Local

To migrate back to local storage:

1. **Download all files** from S3:
   ```bash
   python download_from_s3.py
   ```
2. **Switch to local**: Set `STORAGE_MODE=local`
3. **Verify local files** are accessible

## Performance

### Optimization Tips

1. **Use appropriate regions** to minimize latency
2. **Enable S3 Transfer Acceleration** for global users
3. **Implement caching** for frequently accessed templates
4. **Use multipart uploads** for large files
5. **Configure CloudFront** for file distribution

### Monitoring Metrics

- Template operation latency
- File upload/download speeds
- S3 API call success rates
- Storage costs and usage

## Cost Optimization

1. **Use S3 Intelligent Tiering** for automatic cost optimization
2. **Set up lifecycle policies** to archive old files
3. **Monitor storage usage** with AWS Cost Explorer
4. **Use S3 Storage Classes** appropriately:
   - Standard: Frequently accessed files
   - IA: Infrequently accessed templates
   - Glacier: Long-term archive

## Support

For issues related to S3 integration:

1. Check the `/storage_status` endpoint
2. Review application logs for storage errors
3. Verify AWS credentials and permissions
4. Test S3 connectivity using `python setup_s3.py`
5. Consult AWS S3 documentation for service-specific issues